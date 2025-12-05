"""
RAG (Retrieval-Augmented Generation) module.
"""

from src.rag.query_service import QueryService, get_query_service
from src.rag.web_search import WebSearcher

__all__ = [
    "QueryService",
    "get_query_service",
    "WebSearcher",
]
