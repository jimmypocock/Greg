"""
RAG (Retrieval-Augmented Generation) module.
"""

from api.services.library.rag.query_service import QueryService, get_query_service
from api.services.library.rag.web_search import WebSearcher

__all__ = [
    "QueryService",
    "get_query_service",
    "WebSearcher",
]
