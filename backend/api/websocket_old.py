import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket
from fastapi import WebSocketDisconnect

from backend.core.session import AudioSession
from backend.core.events import EventType


router = APIRouter()

logger = logging.getLogger(__name__)


MAX_CHUNK_BYTES = 1024 * 1024


async def send_event(
    websocket: WebSocket,
    event: EventType,
    data: dict | None = None
):

    message = {
        "type": event.value,
        "data": data or {}
    }

    await websocket.send_json(message)


@router.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket):

    await websocket.accept()

    session = None
    last_stats_time = asyncio.get_running_loop().time()

    logger.info("New WebSocket connection.")

    try:

        while True:

            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                logger.info("WebSocket disconnected.")
                break

            # --------------------------------
            # Binary audio message
            # --------------------------------

            if message.get("bytes") is not None:

                if session is None:
                    await send_event(
                        websocket,
                        EventType.SESSION_ERROR,
                        {"message": "Start a session first."}
                    )
                    continue

                payload = message["bytes"]

                if len(payload) > MAX_CHUNK_BYTES:
                    await send_event(
                        websocket,
                        EventType.SESSION_ERROR,
                        {"message": "Audio chunk too large."}
                    )
                    continue

                try:
                    session.add_audio(payload)

                except ValueError as exc:
                    await send_event(
                        websocket,
                        EventType.SESSION_ERROR,
                        {"message": str(exc)}
                    )
                    continue

                # Send statistics approximately once per second
                now = asyncio.get_running_loop().time()

                if now - last_stats_time >= 1.0:

                    await send_event(
                        websocket,
                        EventType.AUDIO_STATS,
                        session.get_stats()
                    )

                    last_stats_time = now

            # --------------------------------
            # JSON control message
            # --------------------------------

            elif message.get("text") is not None:

                try:
                    data = json.loads(message["text"])

                except json.JSONDecodeError:
                    await send_event(
                        websocket,
                        EventType.SESSION_ERROR,
                        {"message": "Invalid JSON message."}
                    )
                    continue

                event_type = data.get("type")

                # Start session
                if event_type == EventType.SESSION_START.value:

                    if session is not None:
                        await send_event(
                            websocket,
                            EventType.SESSION_ERROR,
                            {"message": "Session already started."}
                        )
                        continue

                    metadata = data.get("data", {})

                    sample_rate = metadata.get("sample_rate")
                    channels = metadata.get("channels", 1)
                    encoding = metadata.get("encoding")

                    if (
                        not isinstance(sample_rate, int)
                        or isinstance(sample_rate, bool)
                        or not 8000 <= sample_rate <= 192000
                        or channels != 1
                        or encoding != "float32"
                    ):
                        await send_event(
                            websocket,
                            EventType.SESSION_ERROR,
                            {"message": "Unsupported audio configuration."}
                        )
                        continue

                    session = AudioSession(
                        sample_rate=sample_rate,
                        channels=channels,
                        encoding=encoding
                    )

                    logger.info(
                        "Session started: %s",
                        session.session_id
                    )

                    await send_event(
                        websocket,
                        EventType.SESSION_READY,
                        {
                            "session_id": session.session_id,
                            "sample_rate": sample_rate
                        }
                    )

                # Stop session
                elif event_type == EventType.AUDIO_END.value:

                    if session is not None:

                        await send_event(
                            websocket,
                            EventType.AUDIO_STATS,
                            session.get_stats()
                        )

                        await send_event(
                            websocket,
                            EventType.SESSION_CLOSED,
                            {
                                "session_id": session.session_id
                            }
                        )

                        logger.info(
                            "Session closed: %s",
                            session.session_id
                        )

                        session = None

    except WebSocketDisconnect:

        logger.info("WebSocket disconnected.")

    except Exception:

        logger.exception("WebSocket error.")

    finally:

        if session is not None:
            logger.info(
                "Session terminated: %s",
                session.session_id
            )