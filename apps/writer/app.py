"""
Writer app - Creative writing assistant with RAG capabilities.

Extends the core app with document processing, Q&A, and web search features.
"""

from fastapi import FastAPI

from packages.core.api.app import create_core_app
from apps.writer.services.ask import register_ask_exception_handlers
from apps.writer.services.documents import register_document_exception_handlers
from apps.writer.services.search import register_search_exception_handlers
from apps.writer.services.storage import register_storage_exception_handlers
from apps.writer.routes import ask, documents, storage, web_search
from apps.writer.routes import admin as writer_admin


def register_writer_routes(app: FastAPI) -> None:
    """Register writer-specific routes."""
    # Document routes (authenticated)
    app.include_router(documents.router, tags=["Documents"])

    # Ask routes (document Q&A, authenticated)
    app.include_router(ask.router, tags=["Ask"])

    # Search routes (web search, authenticated)
    app.include_router(web_search.router, tags=["Search"])

    # Storage routes (authenticated)
    app.include_router(storage.router, tags=["Storage"])

    # Writer-specific admin routes
    app.include_router(writer_admin.router)


def create_app() -> FastAPI:
    """Create the writer application."""
    return create_core_app(
        title="Greg API - Creative Writing Assistant",
        description="Style-aware creative writing assistant with RAG capabilities. "
        "Upload your own writing to inform AI completions.",
        version="2.0.0",
        extra_exception_handlers=[
            register_ask_exception_handlers,
            register_document_exception_handlers,
            register_search_exception_handlers,
            register_storage_exception_handlers,
        ],
        extra_routes_registrar=register_writer_routes,
    )
