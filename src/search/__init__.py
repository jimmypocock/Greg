"""
Web search module.

Provides service, schemas, exceptions, and handlers for web search endpoints.
"""

from src.search.exceptions import (
    EmptyQueryError,
    InvalidModelError,
    SearchError,
    WebSearchError,
)
from src.search.handlers import register_search_exception_handlers
from src.search.schemas import WebSearchRequest
from src.search.service import WebSearchService, get_web_search_service

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
