from enum import StrEnum


class EventType(StrEnum):
    SESSION_START = "session.start"
    SESSION_READY = "session.ready"
    SESSION_ERROR = "session.error"

    AUDIO_END = "audio.end"
    AUDIO_STATS = "audio.stats"

    SESSION_CLOSED = "session.closed"