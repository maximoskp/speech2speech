import numpy as np

from faster_whisper import WhisperModel

from backend.modules.asr.base import (
    ASREngine,
    ASRResult,
    ASRSegment
)


class FasterWhisperASR(ASREngine):

    def __init__(
        self,
        model_size="small",
        device="cpu",
        compute_type="int8"
    ):

        self.model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type
        )

    def transcribe(
        self,
        audio: np.ndarray,
        sample_rate: int,
        language: str | None = None
    ) -> ASRResult:

        if sample_rate != 16000:
            raise ValueError(
                "FasterWhisperASR expects 16 kHz audio."
            )

        audio = np.asarray(
            audio,
            dtype=np.float32
        )

        segments_generator, info = self.model.transcribe(
            audio,
            language=language,
            beam_size=1,
            vad_filter=False,
            condition_on_previous_text=False
        )

        # Important: faster-whisper returns a generator.
        # Iterating over it actually performs transcription.
        segments = list(segments_generator)

        parsed_segments = [
            ASRSegment(
                start=float(segment.start),
                end=float(segment.end),
                text=segment.text.strip()
            )
            for segment in segments
        ]

        text = " ".join(
            segment.text
            for segment in parsed_segments
        ).strip()

        return ASRResult(
            text=text,
            language=info.language,
            language_probability=float(
                info.language_probability
            ),
            segments=parsed_segments
        )