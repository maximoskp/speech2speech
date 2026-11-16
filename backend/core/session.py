import asyncio
from dataclasses import dataclass
import logging

import numpy as np

from backend.audio.buffers import RollingAudioBuffer
from backend.modules.asr.worker import ASRJob


logger = logging.getLogger(__name__)


@dataclass
class SessionStats:

    samples_received: int
    chunks_received: int
    duration_seconds: float
    queue_size: int
    dropped_jobs: int


class AudioSession:

    def __init__(
        self,
        sample_rate: int,
        settings
    ):

        self.sample_rate = sample_rate
        self.settings = settings

        self.buffer = RollingAudioBuffer(
            sample_rate=sample_rate,
            max_seconds=settings.buffer_seconds
        )

        self.queue = asyncio.Queue(
            maxsize=settings.asr_queue_size
        )

        self.samples_received = 0
        self.chunks_received = 0

        self.last_scheduled_end = 0
        self.sequence = 0
        self.dropped_jobs = 0

        self.closed = False

    @property
    def duration_seconds(self):

        return (
            self.samples_received /
            self.sample_rate
        )

    def add_audio(self, audio: np.ndarray):

        if self.closed:
            raise RuntimeError("Session is closed.")

        audio = np.asarray(
            audio,
            dtype=np.float32
        ).reshape(-1)

        if audio.size == 0:
            return None

        self.buffer.append(audio)

        self.samples_received += len(audio)
        self.chunks_received += 1

        return self._schedule_window()

    def _schedule_window(self):

        stride_samples = int(
            self.settings.asr_stride_seconds *
            self.sample_rate
        )

        window_samples = int(
            self.settings.asr_window_seconds *
            self.sample_rate
        )

        min_samples = int(
            self.settings.min_asr_window_seconds *
            self.sample_rate
        )

        end = self.buffer.end_sample

        if end - self.last_scheduled_end < stride_samples:
            return None

        available = min(
            window_samples,
            self.buffer.stored_samples
        )

        if available < min_samples:
            return None

        start = end - available

        audio = self.buffer.get_range(
            start,
            end
        )

        self.sequence += 1

        job = ASRJob(
            audio=audio,
            start_sample=start,
            end_sample=end,
            original_sample_rate=self.sample_rate,
            sequence=self.sequence,
            is_final=False
        )

        try:

            self.queue.put_nowait(job)

        except asyncio.QueueFull:

            self.dropped_jobs += 1

            # Avoid attempting another job for every incoming chunk.
            self.last_scheduled_end = end

            logger.warning(
                "ASR queue full. Dropping partial job."
            )

            return "queue_full"

        self.last_scheduled_end = end

        return "queued"

    async def finish(self):

        if self.closed:
            return

        self.closed = True

        # Create a final transcription job using
        # all audio currently retained in the buffer.
        if self.buffer.stored_samples > 0:

            start = self.buffer.start_sample
            end = self.buffer.end_sample

            audio = self.buffer.get_range(
                start,
                end
            )

            self.sequence += 1

            final_job = ASRJob(
                audio=audio,
                start_sample=start,
                end_sample=end,
                original_sample_rate=self.sample_rate,
                sequence=self.sequence,
                is_final=True
            )

            # Deliberately wait if the queue is full.
            # Final transcription should not be dropped.
            await self.queue.put(final_job)

        # Sentinel: worker processes previous jobs,
        # then exits.
        await self.queue.put(None)

    def get_stats(self):

        return SessionStats(
            samples_received=self.samples_received,
            chunks_received=self.chunks_received,
            duration_seconds=self.duration_seconds,
            queue_size=self.queue.qsize(),
            dropped_jobs=self.dropped_jobs
        )