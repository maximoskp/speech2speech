
import asyncio
import logging

from dataclasses import dataclass

from backend.modules.llm.conversation import Conversation


logger = logging.getLogger(__name__)


@dataclass
class LLMJob:

    transcript: str
    sequence: int


async def run_llm_worker(
    queue: asyncio.Queue,
    conversation: Conversation,
    emit,
    inference_semaphore: asyncio.Semaphore
):

    while True:

        job = await queue.get()

        try:

            if job is None:
                return

            await emit(
                "llm.status",
                {
                    "state": "processing",
                    "sequence": job.sequence
                }
            )

            async with inference_semaphore:

                result = await conversation.process(
                    job.transcript
                )

            await emit(
                "llm.result",
                {
                    "sequence": job.sequence,
                    "transcript": result.transcript,
                    "response": result.response
                }
            )

        except asyncio.CancelledError:

            raise

        except Exception as exc:

            logger.exception("LLM processing failed.")

            try:

                await emit(
                    "llm.error",
                    {
                        "sequence": (
                            job.sequence
                            if job is not None else None
                        ),
                        "message": str(exc)
                    }
                )

            except Exception:

                logger.exception(
                    "Could not send LLM error event."
                )

        finally:

            queue.task_done()
