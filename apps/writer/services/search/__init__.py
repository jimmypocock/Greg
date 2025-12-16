"""
Web search module.

Provides service, schemas, exceptions, and handlers for web search endpoints.
"""

from apps.writer.services.search.exceptions import (
    EmptyQueryError,
    InvalidModelError,
    SearchError,
    WebSearchError,
)
from apps.writer.services.search.handlers import register_search_exception_handlers
from apps.writer.services.search.schemas import WebSearchRequest
from apps.writer.services.search.service import WebSearchService, get_web_search_service

__all__ = [
    # Exceptions
    "EmptyQueryError",
    "InvalidModelError",
    "SearchError",
    "WebSearchError",
    # Handlers
    "register_search_exception_handlers",
    # Schemas
    "WebSearchRequest",
    # Service
    "WebSearchService",
    "get_web_search_service",
]
