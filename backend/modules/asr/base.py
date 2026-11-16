from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import numpy as np


@dataclass
class ASRSegment:

    start: float
    end: float
    text: str


@dataclass
class ASRResult:

    text: str

    language: str | None = None
    language_probability: float | None = None

    segments: list[ASRSegment] = field(
        default_factory=list
    )


class ASREngine(ABC):

    @abstractmethod
    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int,
        language: str | None = None
    ) -> ASRResult:

        pass