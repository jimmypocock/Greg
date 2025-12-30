"""
Songwriter app - AI-powered songwriting assistant.

A standalone app for structuring, organizing, and completing songs.
Includes reference library with RAG capabilities for research and inspiration.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

from api.routes import agents, audio, billing, collaboration, library, notes, songs, versions, webhooks, yjs_websocket
from api.core.routes import admin, auth
from api.auth.handlers import register_auth_exception_handlers
from api.services.library import (
    register_ask_exception_handlers,
    register_document_exception_handlers,
    register_search_exception_handlers,
    register_storage_exception_handlers,
)
from api.core.routes.websocket import router as websocket_router
from api.config import Config
from api.database import close_database, init_database
from api.services.yjs_provider import yjs_provider
from api.jobs.yjs_sync_worker import yjs_sync_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup resources."""
    # Startup
    await init_database()

    # Initialize Yjs provider with Redis
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    await yjs_provider.initialize(redis_url)

    # Start Yjs sync worker
    await yjs_sync_worker.start()

    yield

    # Shutdown
    await yjs_sync_worker.stop()
    await yjs_provider.shutdown()
    await close_database()


def create_app() -> FastAPI:
    """Create the Songwriter application."""
    app = FastAPI(
        title="Songwriter API",
        description="AI-powered songwriting assistant for structuring and completing songs.",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS configuration - use environment settings for production safety
    # Set CORS_ALLOW_ALL=true for local development
    # Set ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com for production
    if Config.CORS_ALLOW_ALL:
        allow_origins = ["*"]
    else:
        allow_origins = Config.ALLOWED_ORIGINS if Config.ALLOWED_ORIGINS else ["http://localhost:3000"]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    )

    # Register exception handlers
    register_auth_exception_handlers(app)
    register_ask_exception_handlers(app)
    register_document_exception_handlers(app)
    register_search_exception_handlers(app)
    register_storage_exception_handlers(app)

    # Global exception handler for unhandled errors
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catch-all handler for unhandled exceptions.

        Returns a proper JSON response instead of HTML error page.
        """
        logger.exception(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred. Please try again."},
        )

    # Register routes
    app.include_router(admin.router)
    app.include_router(auth.router)
    app.include_router(songs.router)
    app.include_router(notes.router)
    app.include_router(agents.router)
    app.include_router(audio.router)
    app.include_router(versions.router)
    app.include_router(collaboration.router)
    app.include_router(billing.router)
    app.include_router(webhooks.router)
    app.include_router(library.router)
    app.include_router(yjs_websocket.router)
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


# For running directly: uvicorn api.app:app --reload --port 8081
app = create_app()
