"""
OpenAI Embedding Provider

Uses OpenAI's text-embedding-ada-002 or text-embedding-3-small/large models.
Produces 1536-dimension vectors (or 3072 for text-embedding-3-large).
"""

import os
from typing import List, Optional

from langchain_openai import OpenAIEmbeddings
from langchain_core.embeddings import Embeddings


# Model dimensions
OPENAI_EMBEDDING_DIMENSIONS = {
    "text-embedding-ada-002": 1536,
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
}

# Pricing per 1M tokens (as of Dec 2025)
OPENAI_EMBEDDING_PRICING = {
    "text-embedding-ada-002": 0.10,
    "text-embedding-3-small": 0.02,
    "text-embedding-3-large": 0.13,
}


class OpenAIEmbeddingProvider(Embeddings):
    """OpenAI embedding provider with LangChain compatibility."""

    PROVIDER_NAME = "openai"
    DEFAULT_MODEL = "text-embedding-3-small"  # Best price/performance

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
    ):
        self.model = model or self.DEFAULT_MODEL
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._embeddings = None

        if self.api_key:
            self._embeddings = OpenAIEmbeddings(
                model=self.model,
                openai_api_key=self.api_key,
            )

    def is_available(self) -> bool:
        """Check if OpenAI embeddings are available."""
        return self._embeddings is not None and bool(self.api_key)

    def get_dimension(self) -> int:
        """Get the embedding dimension for the current model."""
        return OPENAI_EMBEDDING_DIMENSIONS.get(self.model, 1536)

    def get_pricing(self) -> float:
        """Get pricing per 1M tokens for current model."""
        return OPENAI_EMBEDDING_PRICING.get(self.model, 0.10)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        if not self._embeddings:
            raise ValueError("OpenAI embeddings not initialized. Set OPENAI_API_KEY.")
        return self._embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        if not self._embeddings:
            raise ValueError("OpenAI embeddings not initialized. Set OPENAI_API_KEY.")
        return self._embeddings.embed_query(text)

    @staticmethod
    def list_models() -> list[str]:
        """List available OpenAI embedding models."""
        return list(OPENAI_EMBEDDING_DIMENSIONS.keys())
