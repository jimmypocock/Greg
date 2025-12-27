"""
Library services for document management, RAG, and web search.

This module provides:
- Document upload and processing
- Vector storage with pgvector
- RAG (Retrieval Augmented Generation) queries
- Web search integration
"""

from api.services.library.documents import (
    DocumentService,
    DocumentResponse,
    DocumentDetailResponse,
    DocumentListResponse,
    JobCreatedResponse,
    MessageResponse,
    URLProcessRequest,
    register_document_exception_handlers,
)
from api.services.library.vectorstore import (
    PgVectorStore,
    get_vector_store,
)
from api.services.library.rag import (
    QueryService,
)
from api.services.library.ask import (
    QuestionRequest,
    register_ask_exception_handlers,
)
from api.services.library.search import (
    WebSearchService,
    register_search_exception_handlers,
)
from api.services.library.storage import (
    StorageService,
    register_storage_exception_handlers,
)

__all__ = [
    # Documents
    "DocumentService",
    "DocumentResponse",
    "DocumentDetailResponse",
    "DocumentListResponse",
    "JobCreatedResponse",
    "MessageResponse",
    "URLProcessRequest",
    "register_document_exception_handlers",
    # Vectorstore
    "PgVectorStore",
    "get_vector_store",
    # RAG
    "QueryService",
    # Ask
    "QuestionRequest",
    "register_ask_exception_handlers",
    # Search
    "WebSearchService",
    "register_search_exception_handlers",
    # Storage
    "StorageService",
    "register_storage_exception_handlers",
]
