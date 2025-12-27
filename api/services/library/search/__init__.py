"""
Web search module.

Provides service, schemas, exceptions, and handlers for web search endpoints.
"""

from api.services.library.search.exceptions import (
    EmptyQueryError,
    InvalidModelError,
    SearchError,
    WebSearchError,
)
from api.services.library.search.handlers import register_search_exception_handlers
from api.services.library.search.schemas import WebSearchRequest
from api.services.library.search.service import WebSearchService, get_web_search_service

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
