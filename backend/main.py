from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from pathlib import Path

from backend.api.websocket import router as websocket_router


app = FastAPI(
    title="SingCompany",
    version="0.1.0"
)


# Register WebSocket endpoints
app.include_router(websocket_router)


# Serve the browser interface
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


@app.get("/api/health")
async def health():

    return {
        "status": "ok",
        "application": "SingCompany"
    }