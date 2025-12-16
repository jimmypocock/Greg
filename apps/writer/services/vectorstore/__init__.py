"""
Vector store implementations.

Primary: PgVectorStore (PostgreSQL + pgvector)
Legacy: MemorySafeEmbeddings (for backwards compatibility)
"""

from apps.writer.services.vectorstore.pgvector_store import PgVectorStore, get_vector_store
from apps.writer.services.vectorstore.embeddings import MemorySafeEmbeddings

__all__ = [
    "PgVectorStore",
    "get_vector_store",
    "MemorySafeEmbeddings",
]
