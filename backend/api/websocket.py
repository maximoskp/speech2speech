import asyncio
import json
import logging
from contextlib import suppress

import numpy as np

from fastapi import APIRouter, WebSocket
from fastapi import WebSocketDisconnect

from backend.core.session import AudioSession
from backend.core.events import EventType
from backend.modules.asr.worker import run_asr_worker
from backend.core.config import settings
from backend.modules.llm.conversation import Conversation
from backend.modules.llm.worker import (
    LLMJob,
    run_llm_worker
)


logger = logging.getLogger(__name__)

router = APIRouter()


async def send_event(
    websocket,
    event_type,
    data=None,
    send_lock=None
):

    message = {
        "type": (
            event_type.value
            if isinstance(event_type, EventType)
            else event_type
        ),
        "data": data or {}
    }

    if send_lock is None:

        await websocket.send_json(message)

    else:

        async with send_lock:
            await websocket.send_json(message)


@router.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket):

    await websocket.accept()

    session = None
    worker_task = None

    send_lock = asyncio.Lock()

    loop = asyncio.get_running_loop()

    last_stats_time = loop.time()

    engine = websocket.app.state.asr_engine
    inference_semaphore = websocket.app.state.asr_semaphore

    # One conversation per WebSocket connection.
    llm_engine = websocket.app.state.llm_engine

    conversation = Conversation(llm_engine)

    async def emit(event_type, data=None):

        await send_event(
            websocket,
            event_type,
            data,
            send_lock
        )

    logger.info("WebSocket connected.")

    try:

        while True:

            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                logger.info("WebSocket disconnected.")
                break

            # ==========================================
            # BINARY AUDIO
            # ==========================================

            if message.get("bytes") is not None:

                if session is None:

                    await emit(
                        EventType.SESSION_ERROR,
                        {"message": "No active session."}
                    )

                    continue

                payload = message["bytes"]

                if (
                    len(payload) == 0
                    or len(payload) > settings.max_chunk_bytes
                    or len(payload) % 4 != 0
                ):

                    await emit(
                        EventType.SESSION_ERROR,
                        {"message": "Invalid audio payload."}
                    )

                    continue

                audio = np.frombuffer(
                    payload,
                    dtype="<f4"
                )

                if not np.isfinite(audio).all():

                    await emit(
                        EventType.SESSION_ERROR,
                        {"message": "Audio contains invalid values."}
                    )

                    continue

                # Protect the pipeline from unexpected amplitudes.
                audio = np.clip(audio, -1.0, 1.0)

                scheduling = session.add_audio(audio)

                if scheduling == "queue_full":

                    await emit(
                        EventType.ASR_STATUS,
                        {
                            "state": "queue_full",
                            "dropped_jobs": session.dropped_jobs
                        }
                    )

                elif scheduling == "queued":

                    await emit(
                        EventType.ASR_STATUS,
                        {
                            "state": "queued",
                            "queue_size": session.queue.qsize()
                        }
                    )

                # Periodic statistics
                now = loop.time()

                if (
                    now - last_stats_time
                    >= settings.stats_interval_seconds
                ):

                    stats = session.get_stats()

                    await emit(
                        EventType.AUDIO_STATS,
                        {
                            "duration_seconds": round(
                                stats.duration_seconds, 2
                            ),
                            "samples_received": (
                                stats.samples_received
                            ),
                            "chunks_received": (
                                stats.chunks_received
                            ),
                            "queue_size": stats.queue_size,
                            "dropped_jobs": stats.dropped_jobs
                        }
                    )

                    last_stats_time = now

            # ==========================================
            # JSON CONTROL MESSAGE
            # ==========================================

            elif message.get("text") is not None:

                try:

                    data = json.loads(message["text"])

                    if not isinstance(data, dict):
                        raise ValueError("Expected a JSON object.")

                except (json.JSONDecodeError, ValueError):

                    await emit(
                        EventType.SESSION_ERROR,
                        {"message": "Invalid JSON message."}
                    )

                    continue

                event_type = data.get("type")

                # --------------------------------------
                # SESSION START
                # --------------------------------------

                if event_type == EventType.SESSION_START.value:

                    if session is not None:

                        await emit(
                            EventType.SESSION_ERROR,
                            {"message": "Session already active."}
                        )

                        continue

                    metadata = data.get("data", {})

                    sample_rate = metadata.get("sample_rate")
                    channels = metadata.get("channels")
                    encoding = metadata.get("encoding")

                    if (
                        not isinstance(sample_rate, int)
                        or isinstance(sample_rate, bool)
                        or not 8000 <= sample_rate <= 192000
                        or channels != 1
                        or encoding != "float32le"
                    ):

                        await emit(
                            EventType.SESSION_ERROR,
                            {
                                "message": (
                                    "Unsupported audio configuration."
                                )
                            }
                        )

                        continue

                    session = AudioSession(
                        sample_rate=sample_rate,
                        settings=settings
                    )

                    worker_task = asyncio.create_task(
                        run_asr_worker(
                            queue=session.queue,
                            engine=engine,
                            target_sample_rate=(
                                settings.target_sample_rate
                            ),
                            emit=emit,
                            inference_semaphore=(
                                inference_semaphore
                            ),
                            language=settings.asr_language
                        )
                    )

                    llm_queue = asyncio.Queue(
                        maxsize=settings.llm_queue_size
                    )

                    llm_worker_task = asyncio.create_task(
                        run_llm_worker(
                            queue=llm_queue,
                            conversation=conversation,
                            emit=emit,
                            inference_semaphore=(
                                websocket.app.state.llm_semaphore
                            )
                        )
                    )

                    await emit(
                        EventType.SESSION_READY,
                        {
                            "sample_rate": sample_rate,
                            "target_sample_rate": (
                                settings.target_sample_rate
                            ),
                            "buffer_seconds": (
                                settings.buffer_seconds
                            )
                        }
                    )

                    logger.info(
                        "Session started: sample_rate=%s",
                        sample_rate
                    )

                # --------------------------------------
                # AUDIO END
                # --------------------------------------

                elif event_type == EventType.AUDIO_END.value:

                    if session is None:
                        continue

                    await session.finish()

                    if worker_task is not None:
                        await worker_task

                    stats = session.get_stats()

                    await emit(
                        EventType.AUDIO_STATS,
                        {
                            "duration_seconds": round(
                                stats.duration_seconds, 2
                            ),
                            "chunks_received": stats.chunks_received,
                            "dropped_jobs": stats.dropped_jobs
                        }
                    )

                    await emit(
                        EventType.SESSION_CLOSED,
                        {
                            "duration_seconds": round(
                                stats.duration_seconds, 2
                            )
                        }
                    )

                    logger.info(
                        "Session finished: %.2f seconds",
                        stats.duration_seconds
                    )

                    session = None
                    worker_task = None

    except WebSocketDisconnect:

        logger.info("WebSocket disconnected.")

    except Exception:

        logger.exception("WebSocket handler failed.")

    finally:

        if worker_task is not None and not worker_task.done():

            worker_task.cancel()

            with suppress(asyncio.CancelledError):
                await worker_task

        logger.info("WebSocket cleanup completed.")