"""
Models route.

Provides information about available LLM providers and models.

Endpoints:
    GET /models - List available LLM models and providers
"""

import logging
import os
from typing import Annotated

from fastapi import APIRouter, Depends

from packages.core.api.dependencies import get_config
from packages.core.config.settings import Config
from packages.core.llm import (
    DefaultModelInfo,
    ModelInfo,
    ModelsListResponse,
    ProviderInfo,
    RecommendedModel,
)

RECOMMENDED_MODELS = {
    "anthropic": [
        RecommendedModel(
            name="claude-sonnet-4-5-20250929",
            description="Primary - highest quality",
        ),
        RecommendedModel(
            name="claude-haiku-4-5-20251015",
            description="Budget - fast and cost-effective",
        ),
    ],
    "google": [
        RecommendedModel(
            name="gemini-2.5-flash",
            description="Primary - production ready",
        ),
        RecommendedModel(
            name="gemini-2.5-flash-lite",
            description="Budget - fastest, lowest cost",
        ),
    ],
    "openai": [
        RecommendedModel(
            name="gpt-5.1",
            description="Primary - best with caching",
        ),
        RecommendedModel(
            name="gpt-5-mini",
            description="Budget option",
        ),
    ],
}

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["Models"])


# Public functions


@router.get("", response_model=ModelsListResponse)
async def list_models(
    config: Annotated[Config, Depends(get_config)],
):
    """List available LLM models and providers."""
    providers = {
        "anthropic": _get_cloud_provider("anthropic", "ANTHROPIC_API_KEY"),
        "google": _get_cloud_provider("google", "GOOGLE_API_KEY"),
        "ollama": _get_ollama_provider(),
        "openai": _get_cloud_provider("openai", "OPENAI_API_KEY"),
    }

    return ModelsListResponse(
        default=DefaultModelInfo(
            model=config.LLM_MODEL,
            provider=config.LLM_PROVIDER,
        ),
        providers=providers,
    )


# Private functions


def _get_cloud_provider(provider: str, env_var: str) -> ProviderInfo:
    """Get cloud provider info."""
    api_key = os.getenv(env_var, "").strip()
    available = bool(api_key)

    return ProviderInfo(
        available=available,
        reason=None if available else f"{env_var} not set",
        recommended=RECOMMENDED_MODELS.get(provider, []),
    )


def _get_ollama_provider() -> ProviderInfo:
    """Get Ollama provider info with installed models."""
    try:
        import ollama

        response = ollama.list()
        models = []

        for model in response.models:
            size_bytes = model.get("size", 0)
            if size_bytes > 1024**3:
                size = f"{size_bytes / (1024**3):.1f}GB"
            elif size_bytes > 1024**2:
                size = f"{size_bytes / (1024**2):.1f}MB"
            else:
                size = f"{size_bytes}B"

            models.append(
                ModelInfo(
                    name=model.get("model", "unknown"),
                    size=size,
                )
            )

        return ProviderInfo(
            available=len(models) > 0,
            models=models,
            reason=None if models else "No models installed",
        )

    except Exception as e:
        logger.warning(f"Could not fetch Ollama models: {e}")
        return ProviderInfo(
            available=False,
            models=[],
            reason="Ollama not running",
        )
