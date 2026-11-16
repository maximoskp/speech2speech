from contextlib import asynccontextmanager
from pathlib import Path
import logging
import asyncio

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from backend.api.websocket import router as websocket_router
from backend.core.config import settings
from backend.modules.asr.faster_whisper import FasterWhisperASR


logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):

    logging.info("Initializing SingCompany...")

    # Load one shared ASR model.
    app.state.asr_engine = FasterWhisperASR(
        model_size=settings.asr_model,
        device=settings.asr_device,
        compute_type=settings.asr_compute_type
    )

    # Initially, serialize model inference across sessions.
    app.state.asr_semaphore = asyncio.Semaphore(1)

    logging.info("ASR engine initialized.")

    yield

    logging.info("Shutting down SingCompany...")


app = FastAPI(
    title="SingCompany",
    version="0.2.0",
    lifespan=lifespan
)


app.include_router(websocket_router)


@app.get("/api/health")
async def health():

    return {
        "status": "ok",
        "application": "SingCompany"
    }


PROJECT_ROOT = Path(__file__).resolve().parent.parent

FRONTEND_DIR = PROJECT_ROOT / "frontend"

app.mount(
    "/",
    StaticFiles(
        directory=FRONTEND_DIR,
        html=True
    ),
    name="frontend"
)