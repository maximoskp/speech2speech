from collections import deque

import numpy as np


class RollingAudioBuffer:

    def __init__(
        self,
        sample_rate: int,
        max_seconds: float = 30.0
    ):

        self.sample_rate = sample_rate

        self.max_samples = int(
            sample_rate * max_seconds
        )

        self.chunks = deque()

        self.total_samples = 0
        self.stored_samples = 0
        self.start_sample = 0

    @property
    def end_sample(self):
        return self.total_samples

    @property
    def duration_seconds(self):
        return self.stored_samples / self.sample_rate

    def append(self, audio: np.ndarray):

        audio = np.asarray(audio, dtype=np.float32).reshape(-1)

        if audio.size == 0:
            return

        if not np.isfinite(audio).all():
            raise ValueError("Audio contains non-finite values.")

        # Keep an independent copy of the incoming samples.
        audio = audio.copy()

        chunk_start = self.total_samples

        self.chunks.append((chunk_start, audio))

        self.total_samples += len(audio)
        self.stored_samples += len(audio)

        # Remove old samples when the buffer is full.
        while self.stored_samples > self.max_samples:

            excess = self.stored_samples - self.max_samples

            old_start, old_audio = self.chunks[0]

            if len(old_audio) <= excess:

                self.chunks.popleft()

                self.stored_samples -= len(old_audio)

            else:

                self.chunks[0] = (
                    old_start + excess,
                    old_audio[excess:]
                )

                self.stored_samples -= excess

        if self.chunks:

            self.start_sample = self.chunks[0][0]

        else:

            self.start_sample = self.total_samples

    def get_range(
        self,
        start_sample: int,
        end_sample: int
    ) -> np.ndarray:

        if start_sample < self.start_sample:
            raise ValueError("Requested audio has been discarded.")

        if end_sample > self.total_samples:
            raise ValueError("Requested audio is not available yet.")

        if end_sample <= start_sample:
            return np.empty(0, dtype=np.float32)

        pieces = []

        for chunk_start, audio in self.chunks:

            chunk_end = chunk_start + len(audio)

            overlap_start = max(
                start_sample,
                chunk_start
            )

            overlap_end = min(
                end_sample,
                chunk_end
            )

            if overlap_end <= overlap_start:
                continue

            local_start = overlap_start - chunk_start
            local_end = overlap_end - chunk_start

            pieces.append(
                audio[local_start:local_end]
            )

        if not pieces:
            return np.empty(0, dtype=np.float32)

        return np.concatenate(pieces)

    def get_recent(self, num_samples: int) -> np.ndarray:

        num_samples = min(
            num_samples,
            self.stored_samples
        )

        return self.get_range(
            self.total_samples - num_samples,
            self.total_samples
        )

    def clear(self):

        self.chunks.clear()

        self.total_samples = 0
        self.stored_samples = 0
        self.start_sample = 0