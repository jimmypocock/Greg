"""
Models route.

Endpoints:
    GET /models - List available LLM models and providers
"""

import logging
import os

from fastapi import APIRouter, Depends

from src.api.dependencies import get_config
from src.config.settings import Config

RECOMMENDED_MODELS = {
    "openai": [
        {"name": "gpt-5.1", "description": "Primary - best with caching"},
        {"name": "gpt-5-mini", "description": "Budget option"},
    ],
    "anthropic": [
        {"name": "claude-sonnet-4-5-20250929", "description": "Primary - highest quality"},
        {"name": "claude-haiku-4-5-20251015", "description": "Budget - fast and cost-effective"},
    ],
    "google": [
        {"name": "gemini-2.5-flash", "description": "Primary - production ready"},
        {"name": "gemini-2.5-flash-lite", "description": "Budget - fastest, lowest cost"},
    ],
}

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["Models"])


# Public functions

@router.get("")
async def list_models(config: Config = Depends(get_config)):
    """List available LLM models and providers."""
    providers = {
        "ollama": _get_ollama_provider(),
        "openai": _get_cloud_provider("openai", "OPENAI_API_KEY"),
        "anthropic": _get_cloud_provider("anthropic", "ANTHROPIC_API_KEY"),
        "google": _get_cloud_provider("google", "GOOGLE_API_KEY"),
    }

    return {
        "default": {
            "provider": config.LLM_PROVIDER,
            "model": config.LLM_MODEL,
        },
        "providers": providers,
    }


# Private functions

def _get_cloud_provider(provider: str, env_var: str) -> dict:
    """Get cloud provider info."""
    api_key = os.getenv(env_var, "").strip()
    available = bool(api_key)

    result = {
        "available": available,
        "recommended": RECOMMENDED_MODELS.get(provider, []),
    }

    if not available:
        result["reason"] = f"{env_var} not set"

    return result


def _get_ollama_provider() -> dict:
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

            models.append({
                "name": model.get("model", "unknown"),
                "size": size,
            })

        return {
            "available": len(models) > 0,
            "reason": None if models else "No models installed",
            "models": models,
        }

    except Exception as e:
        logger.warning(f"Could not fetch Ollama models: {e}")
        return {
            "available": False,
            "reason": "Ollama not running",
            "models": [],
        }
