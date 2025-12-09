"""
FastAPI application factory.

Creates and configures the FastAPI application with all routes and middleware.
"""

import logging

from fastapi import FastAPI

from src.config import Config
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.api.lifespan import lifespan
from src.api.rate_limit import limiter
from src.admin import register_admin_exception_handlers
from src.api_keys import register_api_key_exception_handlers
from src.ask import register_ask_exception_handlers
from src.auth import register_auth_exception_handlers
from src.documents import register_document_exception_handlers
from src.jobs import register_job_exception_handlers
from src.search import register_search_exception_handlers
from src.storage import register_storage_exception_handlers
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
    storage,
    web_search,
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

    # Configure exception handlers
    _configure_exception_handlers(app)

    # Register routes
    _register_routes(app)

    return app


def _configure_cors(app: FastAPI) -> None:
    """Configure CORS middleware."""
    cors_origins = Config.ALLOWED_ORIGINS

    # Default development origins if not configured
    if not cors_origins:
        cors_origins = [
            "http://localhost:3000",  # NextJS default
            "http://localhost:5173",  # Vite default
            "http://localhost:8080",  # API itself (for OpenAPI docs)
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
        ]

    allow_all_origins = Config.CORS_ALLOW_ALL

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if allow_all_origins else cors_origins,
        allow_credentials=not allow_all_origins,  # Can't use credentials with wildcard
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )


def _configure_exception_handlers(app: FastAPI) -> None:
    """Configure exception handlers for domain exceptions."""
    register_admin_exception_handlers(app)
    register_api_key_exception_handlers(app)
    register_ask_exception_handlers(app)
    register_auth_exception_handlers(app)
    register_document_exception_handlers(app)
    register_job_exception_handlers(app)
    register_search_exception_handlers(app)
    register_storage_exception_handlers(app)


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
    app.include_router(web_search.router, tags=["Search"])

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
