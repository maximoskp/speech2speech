from enum import StrEnum


class EventType(StrEnum):

    # Session lifecycle
    SESSION_START = "session.start"
    SESSION_READY = "session.ready"
    SESSION_ERROR = "session.error"
    SESSION_CLOSED = "session.closed"

    # Audio
    AUDIO_END = "audio.end"
    AUDIO_STATS = "audio.stats"

    # ASR
    ASR_STATUS = "asr.status"
    ASR_PARTIAL = "asr.partial"
    ASR_FINAL = "asr.final"
    ASR_ERROR = "asr.error"

    # LLM
    LLM_STATUS = "llm.status"
    LLM_RESULT = "llm.result"
    LLM_ERROR = "llm.error"

    # Conversation
    CONVERSATION_RESET = "conversation.reset"
    CONVERSATION_READY = "conversation.ready"
