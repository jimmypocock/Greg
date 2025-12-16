"""
Embedding Provider Factory

Provides runtime selection of embedding providers based on configuration.

Usage:
    from packages.core.llm.embeddings import get_embeddings, get_embedding_dimension

    # Get default provider (from .env)
    embeddings = get_embeddings()

    # Or specify at runtime
    embeddings = get_embeddings("openai")  # 1536 dimensions
    embeddings = get_embeddings("local")   # 384 dimensions

    # Get embedding dimension for current provider
    dim = get_embedding_dimension()
"""

from .factory import (
    get_embeddings,
    get_embedding_dimension,
    get_available_embedding_providers,
    EMBEDDING_DIMENSIONS,
)
from .openai_embeddings import OpenAIEmbeddingProvider
from .local_embeddings import LocalEmbeddingProvider

__all__ = [
    "get_embeddings",
    "get_embedding_dimension",
    "get_available_embedding_providers",
    "EMBEDDING_DIMENSIONS",
    "OpenAIEmbeddingProvider",
    "LocalEmbeddingProvider",
]
