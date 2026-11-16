import asyncio
import logging
from dataclasses import dataclass

import numpy as np

from backend.audio.resampling import resample_audio
from backend.modules.asr.base import ASREngine


logger = logging.getLogger(__name__)


@dataclass
class ASRJob:

    audio: np.ndarray

    start_sample: int
    end_sample: int

    original_sample_rate: int

    sequence: int

    is_final: bool = False


async def run_asr_worker(
    queue: asyncio.Queue,
    engine: ASREngine,
    target_sample_rate: int,
    emit,
    inference_semaphore: asyncio.Semaphore,
    language=None
):

    while True:

        job = await queue.get()

        try:

            if job is None:
                return

            await emit(
                "asr.status",
                {
                    "state": "processing",
                    "sequence": job.sequence
                }
            )

            # Resample outside the model inference call.
            audio_16k = resample_audio(
                job.audio,
                original_rate=job.original_sample_rate,
                target_rate=target_sample_rate
            )

            # faster-whisper is blocking.
            # Keep it outside the event loop.
            async with inference_semaphore:

                result = await asyncio.to_thread(
                    engine.transcribe,
                    audio_16k,
                    target_sample_rate,
                    language
                )

            event_type = (
                "asr.final"
                if job.is_final
                else "asr.partial"
            )

            await emit(
                event_type,
                {
                    "sequence": job.sequence,
                    "text": result.text,
                    "language": result.language,
                    "language_probability": (
                        result.language_probability
                    ),
                    "window_start": (
                        job.start_sample /
                        job.original_sample_rate
                    ),
                    "window_end": (
                        job.end_sample /
                        job.original_sample_rate
                    ),
                    "segments": [
                        {
                            "start": (
                                job.start_sample / job.original_sample_rate
                            ) + segment.start,

                            "end": (
                                job.start_sample / job.original_sample_rate
                            ) + segment.end,
                            "text": segment.text
                        }
                        for segment in result.segments
                    ]
                }
            )

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            logger.exception("ASR processing failed.")

            try:
                await emit(
                    "asr.error",
                    {
                        "sequence": (
                            job.sequence
                            if job is not None else None
                        ),
                        "message": str(exc)
                    }
                )

            except Exception:
                logger.exception(
                    "Could not send ASR error event."
                )

        finally:

            queue.task_done()