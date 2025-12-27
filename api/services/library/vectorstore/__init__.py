"""
Vector store implementations.

Primary: PgVectorStore (PostgreSQL + pgvector)
Legacy: MemorySafeEmbeddings (for backwards compatibility)
"""

from api.services.library.vectorstore.pgvector_store import PgVectorStore, get_vector_store
from api.services.library.vectorstore.embeddings import MemorySafeEmbeddings

__all__ = [
    "PgVectorStore",
    "get_vector_store",
    "MemorySafeEmbeddings",
]
