"""
Songwriter app - AI-powered songwriting assistant.

A standalone app for structuring, organizing, and completing songs.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.songwriter.routes import agents, audio, notes, songs
from packages.core.api.routes.websocket import router as websocket_router
from packages.core.database import close_database, init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources."""
    # Startup
    await init_database()
    yield
    # Shutdown
    await close_database()


def create_app() -> FastAPI:
    """Create the Songwriter application."""
    app = FastAPI(
        title="Songwriter API",
        description="AI-powered songwriting assistant for structuring and completing songs.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS for local development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routes
    app.include_router(songs.router)
    app.include_router(notes.router)
    app.include_router(agents.router)
    app.include_router(audio.router)
    app.include_router(websocket_router)

    # Health check
    @app.get("/health")
    async def health():
        return {"status": "ok", "app": "songwriter"}

    # Root info
    @app.get("/")
    async def root():
        return {
            "app": "Songwriter API",
            "version": "0.1.0",
            "description": "AI-powered songwriting assistant",
        }

    return app


# For running directly: uvicorn apps.songwriter.app:app --reload --port 8081
app = create_app()
