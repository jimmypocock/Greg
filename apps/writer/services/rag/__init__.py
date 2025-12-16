"""
RAG (Retrieval-Augmented Generation) module.
"""

from apps.writer.services.rag.query_service import QueryService, get_query_service
from apps.writer.services.rag.web_search import WebSearcher

__all__ = [
    "QueryService",
    "get_query_service",
    "WebSearcher",
]
