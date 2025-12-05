"""
Local Embedding Provider

Uses HuggingFace sentence-transformers models that run locally on CPU.
Free, private, no API calls required.
"""

import os
import warnings
from typing import List, Optional

from langchain_core.embeddings import Embeddings


# Model dimensions for common local models
LOCAL_EMBEDDING_DIMENSIONS = {
    "all-MiniLM-L6-v2": 384,
    "all-MiniLM-L12-v2": 384,
    "all-mpnet-base-v2": 768,
    "multi-qa-MiniLM-L6-cos-v1": 384,
    "paraphrase-MiniLM-L6-v2": 384,
    "sentence-t5-base": 768,
    # Larger models
    "all-distilroberta-v1": 768,
    "multi-qa-mpnet-base-dot-v1": 768,
}


class LocalEmbeddingProvider(Embeddings):
    """Local HuggingFace embedding provider with memory safety."""

    PROVIDER_NAME = "local"
    DEFAULT_MODEL = "all-MiniLM-L6-v2"

    def __init__(
        self,
        model: Optional[str] = None,
        batch_size: int = 2,
        device: str = "cpu",
    ):
        self.model_name = model or self.DEFAULT_MODEL
        self.batch_size = batch_size
        self.device = device
        self._embeddings = None
        self._base_embeddings = None

        # Initialize lazily to avoid import time overhead
        self._initialize()

    def _initialize(self):
        """Initialize embeddings with memory safety."""
        from langchain_huggingface import HuggingFaceEmbeddings
        from src.vectorstore.embeddings import MemorySafeEmbeddings

        # Prevent HuggingFace from making HTTP requests
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        os.environ["HF_DATASETS_OFFLINE"] = "1"

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore", message=".*clean_up_tokenization_spaces.*"
            )

            try:
                self._base_embeddings = HuggingFaceEmbeddings(
                    model_name=self.model_name,
                    model_kwargs={
                        "device": self.device,
                        "trust_remote_code": False,
                        "local_files_only": True,
                    },
                    encode_kwargs={
                        "normalize_embeddings": True,
                        "batch_size": self.batch_size,
                    },
                )
            except Exception:
                # If local_files_only fails, try without it
                self._base_embeddings = HuggingFaceEmbeddings(
                    model_name=self.model_name,
                    model_kwargs={
                        "device": self.device,
                        "trust_remote_code": False,
                    },
                    encode_kwargs={
                        "normalize_embeddings": True,
                        "batch_size": self.batch_size,
                    },
                )

            # Wrap with memory-safe version
            self._embeddings = MemorySafeEmbeddings(
                self._base_embeddings, batch_size=self.batch_size
            )

    def is_available(self) -> bool:
        """Check if local embeddings are available."""
        return self._embeddings is not None

    def get_dimension(self) -> int:
        """Get the embedding dimension for the current model."""
        return LOCAL_EMBEDDING_DIMENSIONS.get(self.model_name, 384)

    def get_pricing(self) -> float:
        """Get pricing (always 0 for local models)."""
        return 0.0

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents."""
        if not self._embeddings:
            raise ValueError("Local embeddings not initialized.")
        return self._embeddings.embed_documents(texts)

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query."""
        if not self._embeddings:
            raise ValueError("Local embeddings not initialized.")
        return self._embeddings.embed_query(text)

    @staticmethod
    def list_models() -> list[str]:
        """List available local embedding models."""
        return list(LOCAL_EMBEDDING_DIMENSIONS.keys())
