"""
Core FastAPI application factory.

Creates and configures the FastAPI application with core routes and middleware.
Apps can extend this with their own routes and exception handlers.
"""

import logging
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from packages.core.api.lifespan import lifespan
from packages.core.api.rate_limit import limiter
from packages.core.admin import register_admin_exception_handlers
from packages.core.api_keys import register_api_key_exception_handlers
from packages.core.auth import register_auth_exception_handlers
from packages.core.auth.middleware import AuthMiddleware
from packages.core.config import Config
from packages.core.jobs import register_job_exception_handlers
from packages.core.api.routes import (
    admin,
    api_keys,
    auth,
    costs,
    health,
    jobs,
    models,
    root,
    websocket,
)

logger = logging.getLogger(__name__)


def create_core_app(
    title: str = "Greg API",
    description: str = "Core API",
    version: str = "2.0.0",
    extra_exception_handlers: list[Callable[[FastAPI], None]] | None = None,
    extra_routes_registrar: Callable[[FastAPI], None] | None = None,
) -> FastAPI:
    """
    Create and configure the core FastAPI application.

    Args:
        title: API title
        description: API description
        version: API version
        extra_exception_handlers: List of functions to register additional exception handlers
        extra_routes_registrar: Function to register additional routes

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title=title,
        description=description,
        version=version,
        lifespan=lifespan,
    )

    # Configure CORS
    _configure_cors(app)

    # Configure auth middleware (sets request.state.user for rate limiting)
    app.add_middleware(AuthMiddleware)

    # Configure rate limiting (per-user when authenticated)
    _configure_rate_limiting(app)

    # Configure core exception handlers
    _configure_core_exception_handlers(app)

    # Configure extra exception handlers from apps
    if extra_exception_handlers:
        for handler in extra_exception_handlers:
            handler(app)

    # Register core routes
    _register_core_routes(app)

    # Register extra routes from apps
    if extra_routes_registrar:
        extra_routes_registrar(app)

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


def _configure_core_exception_handlers(app: FastAPI) -> None:
    """Configure exception handlers for core domain exceptions."""
    register_admin_exception_handlers(app)
    register_api_key_exception_handlers(app)
    register_auth_exception_handlers(app)
    register_job_exception_handlers(app)


def _configure_rate_limiting(app: FastAPI) -> None:
    """Configure rate limiting middleware."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def _register_core_routes(app: FastAPI) -> None:
    """Register core route modules."""
    # Root route (public)
    app.include_router(root.router)

    # Health route (public)
    app.include_router(health.router)

    # Models route (public)
    app.include_router(models.router)

    # Authentication routes (public)
    app.include_router(auth.router)

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
