
import json
import logging

from ollama import AsyncClient

from backend.modules.llm.base import (
    LLMEngine,
    LLMResult,
    SYSTEM_PROMPT
)


logger = logging.getLogger(__name__)


class KrikriEngine(LLMEngine):

    def __init__(
        self,
        host: str = "http://localhost:11434",
        model: str = "ilsp/llama-krikri-8b-instruct",
        temperature: float = 0.2
    ):

        self.model = model
        self.temperature = temperature

        self.client = AsyncClient(host=host)

        logger.info(
            "Initialized Krikri engine: %s",
            model
        )

    async def chat(self, messages: list[dict]) -> str:

        result = await self.client.chat(

            model=self.model,

            messages=messages,

            format="json",

            options={
                "temperature": self.temperature
            },

            stream=False
        )

        return result.message.content

    async def process(
        self,
        messages: list[dict]
    ) -> LLMResult:

        raw_response = await self.chat(messages)

        try:

            data = json.loads(raw_response)

            transcript = data["transcript"]
            response = data["response"]

            if not isinstance(transcript, str):
                raise ValueError("Invalid transcript field.")

            if not isinstance(response, str):
                raise ValueError("Invalid response field.")

            return LLMResult(
                transcript=transcript,
                response=response
            )

        except (json.JSONDecodeError, KeyError, ValueError):

            logger.exception(
                "Could not parse Krikri response."
            )

            # Preserve the generated response rather than
            # losing it because of an unexpected JSON format.

            return LLMResult(
                transcript="",
                response=raw_response
            )
