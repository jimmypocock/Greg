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

from api.core.dependencies import get_config
from api.config.settings import Config
from api.llm import (
    DefaultModelInfo,
    ModelInfo,
    ModelsListResponse,
    ProviderInfo,
    RecommendedModel,
)

# Recommended models for each provider.
# NOTE: These should be reviewed periodically as providers release new models.
# Last updated: 2025-01
RECOMMENDED_MODELS = {
    "anthropic": [
        RecommendedModel(
            name="claude-sonnet-4-5-20250514",
            description="Primary - best balance of quality and speed",
        ),
        RecommendedModel(
            name="claude-haiku-4-5-20250514",
            description="Budget - fast and cost-effective",
        ),
    ],
    "google": [
        RecommendedModel(
            name="gemini-2.0-flash",
            description="Primary - fast and capable",
        ),
        RecommendedModel(
            name="gemini-1.5-flash",
            description="Budget - reliable and cost-effective",
        ),
    ],
    "openai": [
        RecommendedModel(
            name="gpt-4o",
            description="Primary - best quality",
        ),
        RecommendedModel(
            name="gpt-4o-mini",
            description="Budget - fast and affordable",
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
            # Ollama returns model objects with attributes, not dicts
            size_bytes = getattr(model, "size", 0) or 0
            model_name = getattr(model, "model", None) or getattr(model, "name", "unknown")

            if size_bytes > 1024**3:
                size = f"{size_bytes / (1024**3):.1f}GB"
            elif size_bytes > 1024**2:
                size = f"{size_bytes / (1024**2):.1f}MB"
            else:
                size = f"{size_bytes}B"

            models.append(
                ModelInfo(
                    name=model_name,
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
