
from backend.modules.llm.base import LLMEngine, LLMResult, SYSTEM_PROMPT


class Conversation:

    def __init__(self, engine: LLMEngine):

        self.engine = engine

        self.messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]

    async def process(
        self,
        transcript: str
    ) -> LLMResult:

        transcript = transcript.strip()

        if not transcript:
            return LLMResult(
                transcript="",
                response=""
            )

        self.messages.append({
            "role": "user",
            "content": transcript
        })

        try:

            result = await self.engine.process(
                self.messages
            )

            self.messages.append({
                "role": "assistant",
                "content": result.response
            })

            return result

        except Exception:

            # Remove the unanswered user message so that
            # the conversation remains consistent.

            self.messages.pop()

            raise

    def reset(self):

        self.messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT
            }
        ]
