
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:

    # ==========================================
    # AUDIO
    # ==========================================

    target_sample_rate: int = 16000
    buffer_seconds: float = 30.0

    # ==========================================
    # ASR WINDOWS
    # ==========================================

    asr_window_seconds: float = 6.0
    asr_stride_seconds: float = 2.0
    min_asr_window_seconds: float = 2.0

    # ==========================================
    # ASR MODEL
    # ==========================================

    asr_model: str = "small"

    # Options: "cpu", "cuda"
    asr_device: str = "cuda"

    # CPU: "int8"
    # GPU: "float16"
    asr_compute_type: str = "float16"

    # "el" = Greek
    # "en" = English
    # None = automatic detection
    asr_language: str | None = None

    # ==========================================
    # PROCESSING
    # ==========================================

    asr_queue_size: int = 2

    # ==========================================
    # TRANSPORT
    # ==========================================

    max_chunk_bytes: int = 256 * 1024
    stats_interval_seconds: float = 1.0

    # ==========================================
    # TRANSPORT
    # ==========================================

    llm_queue_size: int = 2

    # ==========================================
    # ENVIRONMENT OVERRIDES
    # ==========================================

    @classmethod
    def from_env(cls):

        defaults = cls()

        return cls(

            target_sample_rate=int(
                os.getenv(
                    "TARGET_SAMPLE_RATE",
                    defaults.target_sample_rate
                )
            ),

            buffer_seconds=float(
                os.getenv(
                    "BUFFER_SECONDS",
                    defaults.buffer_seconds
                )
            ),

            asr_window_seconds=float(
                os.getenv(
                    "ASR_WINDOW_SECONDS",
                    defaults.asr_window_seconds
                )
            ),

            asr_stride_seconds=float(
                os.getenv(
                    "ASR_STRIDE_SECONDS",
                    defaults.asr_stride_seconds
                )
            ),

            min_asr_window_seconds=float(
                os.getenv(
                    "MIN_ASR_WINDOW_SECONDS",
                    defaults.min_asr_window_seconds
                )
            ),

            asr_model=os.getenv(
                "ASR_MODEL",
                defaults.asr_model
            ),

            asr_device=os.getenv(
                "ASR_DEVICE",
                defaults.asr_device
            ),

            asr_compute_type=os.getenv(
                "ASR_COMPUTE_TYPE",
                defaults.asr_compute_type
            ),

            asr_language=os.getenv(
                "ASR_LANGUAGE",
                defaults.asr_language
            ) or None,

            asr_queue_size=int(
                os.getenv(
                    "ASR_QUEUE_SIZE",
                    defaults.asr_queue_size
                )
            ),

            max_chunk_bytes=int(
                os.getenv(
                    "MAX_CHUNK_BYTES",
                    defaults.max_chunk_bytes
                )
            ),

            stats_interval_seconds=float(
                os.getenv(
                    "STATS_INTERVAL_SECONDS",
                    defaults.stats_interval_seconds
                )
            )
        )


settings = Settings.from_env()
