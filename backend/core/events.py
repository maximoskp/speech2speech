from enum import StrEnum


class EventType(StrEnum):

    SESSION_START = "session.start"
    SESSION_READY = "session.ready"
    SESSION_ERROR = "session.error"
    SESSION_CLOSED = "session.closed"

    AUDIO_END = "audio.end"
    AUDIO_STATS = "audio.stats"

    ASR_STATUS = "asr.status"
    ASR_PARTIAL = "asr.partial"
    ASR_FINAL = "asr.final"
    ASR_ERROR = "asr.error"