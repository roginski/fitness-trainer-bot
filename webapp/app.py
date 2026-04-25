import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def create_app() -> FastAPI:
    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/trainer")
    async def trainer_app():
        return FileResponse(os.path.join(STATIC_DIR, "trainer.html"))

    @app.get("/trainee")
    async def trainee_app():
        return FileResponse(os.path.join(STATIC_DIR, "trainee.html"))

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app
