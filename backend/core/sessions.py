from dataclasses import dataclass, field
from time import time
from uuid import uuid4


@dataclass
class AudioSession:

    sample_rate: int
    channels: int
    encoding: str = "float32"

    session_id: str = field(
        default_factory=lambda: str(uuid4())
    )

    samples_received: int = 0
    chunks_received: int = 0

    created_at: float = field(
        default_factory=time
    )

    last_audio_at: float | None = None

    @property
    def duration_seconds(self) -> float:
        return self.samples_received / self.sample_rate

    def add_audio(self, payload: bytes):

        # Float32 = 4 bytes per sample
        if len(payload) % 4 != 0:
            raise ValueError(
                "Invalid Float32 audio payload."
            )

        samples = len(payload) // 4

        self.samples_received += samples
        self.chunks_received += 1
        self.last_audio_at = time()

    def get_stats(self):

        return {
            "session_id": self.session_id,
            "samples_received": self.samples_received,
            "chunks_received": self.chunks_received,
            "duration_seconds": round(
                self.duration_seconds, 2
            ),
            "sample_rate": self.sample_rate,
        }