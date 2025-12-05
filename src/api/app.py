"""
FastAPI application factory.

Creates and configures the FastAPI application with all routes and middleware.
"""

import os
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.lifespan import lifespan
from src.api.rate_limit import limiter
from src.api.routes import (
    admin,
    api_keys,
    ask,
    auth,
    costs,
    documents,
    health,
    jobs,
    models,
    root,
    search,
    storage,
    websocket,
)

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Greg API - AI Playground",
        description="100% Free, Local, and Private Document Question Answering. "
        "Supports PDF, TXT, CSV, Markdown, Word, Excel, and Image files.",
        version="2.0.0",
        lifespan=lifespan,
    )

    # Configure CORS
    _configure_cors(app)

    # Configure rate limiting
    _configure_rate_limiting(app)

    # Register routes
    _register_routes(app)

    return app


def _configure_cors(app: FastAPI) -> None:
    """Configure CORS middleware."""
    # Get origins from environment
    cors_origins = os.environ.get("ALLOWED_ORIGINS", "").split(",")
    cors_origins = [o.strip() for o in cors_origins if o.strip()]

    # Default development origins if not configured
    if not cors_origins:
        cors_origins = [
            "http://localhost:3000",  # NextJS default
            "http://localhost:5173",  # Vite default
            "http://localhost:8080",  # API itself (for OpenAPI docs)
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]

    # Allow all origins in development mode
    allow_all_origins = os.environ.get("CORS_ALLOW_ALL", "false").lower() == "true"

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all_origins else cors_origins,
        allow_credentials=not allow_all_origins,  # Can't use credentials with wildcard
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )


def _configure_rate_limiting(app: FastAPI) -> None:
    """Configure rate limiting middleware."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def _register_routes(app: FastAPI) -> None:
    """Register all route modules."""
    # Root route (public)
    app.include_router(root.router)

    # Health route (public)
    app.include_router(health.router)

    # Models route (public)
    app.include_router(models.router)

    # Authentication routes (public)
    app.include_router(auth.router)

    # Document routes (authenticated)
    app.include_router(documents.router, tags=["Documents"])

    # Ask routes (document Q&A, authenticated)
    app.include_router(ask.router, tags=["Ask"])

    # Search routes (web search, authenticated)
    app.include_router(search.router, tags=["Search"])

    # Storage routes (authenticated)
    app.include_router(storage.router, tags=["Storage"])

    # Job routes (authenticated)
    app.include_router(jobs.router, tags=["Jobs"])

    # API key management (authenticated)
    app.include_router(api_keys.router)

    # Cost tracking routes (authenticated)
    app.include_router(costs.router, tags=["Costs"])

    # Admin routes (admin only)
    app.include_router(admin.router)

    # WebSocket routes
    app.include_router(websocket.router, tags=["WebSocket"])


