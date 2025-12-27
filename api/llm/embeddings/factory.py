"""
Embedding Provider Factory

Provides runtime selection of embedding providers based on configuration.
"""

import os
from typing import Optional

from langchain_core.embeddings import Embeddings

from api.config import Config

from .openai_embeddings import OpenAIEmbeddingProvider, OPENAI_EMBEDDING_DIMENSIONS
from .local_embeddings import LocalEmbeddingProvider, LOCAL_EMBEDDING_DIMENSIONS


# Combined dimensions lookup
EMBEDDING_DIMENSIONS = {
    **OPENAI_EMBEDDING_DIMENSIONS,
    **LOCAL_EMBEDDING_DIMENSIONS,
}

# Provider registry
PROVIDERS = {
    "openai": OpenAIEmbeddingProvider,
    "local": LocalEmbeddingProvider,
    "huggingface": LocalEmbeddingProvider,  # Alias
    "sentence-transformers": LocalEmbeddingProvider,  # Alias
}


def get_embeddings(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> Embeddings:
    """
    Get an embedding provider instance.

    Args:
        provider: Provider name ("openai", "local").
                  Defaults to EMBEDDING_PROVIDER env var, then "openai" if
                  OPENAI_API_KEY is set, otherwise "local".
        model: Model name. Defaults to EMBEDDING_MODEL env var, then provider default.
        **kwargs: Additional arguments passed to provider.

    Returns:
        Configured embedding provider instance.

    Raises:
        ValueError: If provider is unknown.
    """
    # Get provider from config if not specified
    if provider is None:
        provider = Config.EMBEDDING_PROVIDER

        # Auto-detect provider based on available API keys
        if provider is None:
            openai_key = os.getenv("OPENAI_API_KEY", "").strip()
            if openai_key:
                provider = "openai"
            else:
                provider = "local"

    provider = provider.lower().strip()

    # Get provider class
    if provider not in PROVIDERS:
        available = ["openai", "local"]
        raise ValueError(
            f"Unknown embedding provider: {provider}. "
            f"Available: {', '.join(available)}"
        )

    provider_class = PROVIDERS[provider]

    # Get model from config if not specified
    if model is None:
        model = Config.EMBEDDING_MODEL

    return provider_class(model=model, **kwargs)


def get_embedding_dimension(
    provider: Optional[str] = None,
    model: Optional[str] = None,
) -> int:
    """
    Get the embedding dimension for a provider/model combination.

    Args:
        provider: Provider name. Defaults to configured provider.
        model: Model name. Defaults to configured model.

    Returns:
        Embedding dimension (e.g., 1536 for OpenAI, 384 for all-MiniLM-L6-v2).
    """
    embeddings = get_embeddings(provider, model)
    return embeddings.get_dimension()


def get_available_embedding_providers() -> dict[str, dict]:
    """
    Get information about available embedding providers.

    Returns:
        Dict mapping provider names to their availability info.
    """
    result = {}

    # Check OpenAI
    openai = OpenAIEmbeddingProvider()
    result["openai"] = {
        "available": openai.is_available(),
        "models": OpenAIEmbeddingProvider.list_models(),
        "default_model": OpenAIEmbeddingProvider.DEFAULT_MODEL,
        "dimension": 1536,
        "pricing_per_1m_tokens": 0.02,  # text-embedding-3-small
        "reason": None if openai.is_available() else "OPENAI_API_KEY not set",
    }

    # Check Local
    try:
        local = LocalEmbeddingProvider()
        local_available = local.is_available()
        local_reason = None
    except Exception as e:
        local_available = False
        local_reason = str(e)

    result["local"] = {
        "available": local_available,
        "models": LocalEmbeddingProvider.list_models(),
        "default_model": LocalEmbeddingProvider.DEFAULT_MODEL,
        "dimension": 384,
        "pricing_per_1m_tokens": 0.0,  # Free
        "reason": local_reason,
    }

    return result


def get_default_embedding_info() -> dict:
    """Get info about the currently configured default embedding provider."""
    provider_name = Config.EMBEDDING_PROVIDER
    model_name = Config.EMBEDDING_MODEL

    # Auto-detect if not specified
    if provider_name is None:
        openai_key = os.getenv("OPENAI_API_KEY", "").strip()
        provider_name = "openai" if openai_key else "local"

    try:
        provider = get_embeddings(provider_name, model_name)
        return {
            "provider": provider_name,
            "model": getattr(provider, "model", None)
            or getattr(provider, "model_name", None),
            "available": provider.is_available(),
            "dimension": provider.get_dimension(),
            "pricing_per_1m_tokens": provider.get_pricing(),
        }
    except ValueError as e:
        return {
            "provider": provider_name,
            "model": model_name,
            "available": False,
            "error": str(e),
        }
