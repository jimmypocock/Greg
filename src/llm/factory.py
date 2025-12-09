"""
LLM Provider Factory

Provides runtime selection of LLM providers based on request parameters
or environment configuration.

Usage:
    from src.llm import get_provider, get_available_providers

    # Get default provider (from .env)
    llm = get_provider()

    # Or specify at runtime
    llm = get_provider("anthropic", model="claude-3-5-haiku")
    llm = get_provider("openai", model="gpt-4o-mini")
    llm = get_provider("google", model="gemini-1.5-flash")
    llm = get_provider("ollama", model="mistral")
"""

from typing import Optional

from src.config import Config

from .base import BaseLLMProvider
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider
from .google_provider import GoogleProvider
from .ollama_provider import OllamaProvider


# Provider registry
PROVIDERS = {
    "anthropic": AnthropicProvider,
    "claude": AnthropicProvider,  # Alias
    "openai": OpenAIProvider,
    "gpt": OpenAIProvider,  # Alias
    "google": GoogleProvider,
    "gemini": GoogleProvider,  # Alias
    "ollama": OllamaProvider,
    "local": OllamaProvider,  # Alias
}


def get_provider(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    **kwargs,
) -> BaseLLMProvider:
    """
    Get an LLM provider instance.

    Args:
        provider: Provider name ("anthropic", "openai", "google", "ollama").
                  Defaults to LLM_PROVIDER env var, then "ollama".
        model: Model name. Defaults to LLM_MODEL env var, then provider default.
        **kwargs: Additional arguments passed to provider (temperature, max_tokens, etc.)

    Returns:
        Configured LLM provider instance.

    Raises:
        ValueError: If provider is unknown.
    """
    # Get provider from config if not specified
    if provider is None:
        provider = Config.LLM_PROVIDER

    provider = provider.lower().strip()

    # Get provider class
    if provider not in PROVIDERS:
        available = list(set(PROVIDERS.keys()) - {"claude", "gpt", "gemini", "local"})
        raise ValueError(
            f"Unknown provider: {provider}. "
            f"Available: {', '.join(sorted(available))}"
        )

    provider_class = PROVIDERS[provider]

    # Get model from config if not specified
    if model is None:
        model = Config.LLM_MODEL

    return provider_class(model=model, **kwargs)


def get_available_providers() -> dict[str, dict]:
    """
    Get information about available providers.

    Returns:
        Dict mapping provider names to their availability info.
    """
    result = {}

    # Check Anthropic
    anthropic = AnthropicProvider()
    result["anthropic"] = {
        "available": anthropic.is_available(),
        "models": AnthropicProvider.list_models(),
        "default_model": AnthropicProvider.DEFAULT_MODEL,
        "reason": None if anthropic.is_available() else "ANTHROPIC_API_KEY not set",
    }

    # Check OpenAI
    openai = OpenAIProvider()
    result["openai"] = {
        "available": openai.is_available(),
        "models": OpenAIProvider.list_models(),
        "default_model": OpenAIProvider.DEFAULT_MODEL,
        "reason": None if openai.is_available() else "OPENAI_API_KEY not set",
    }

    # Check Google
    google = GoogleProvider()
    result["google"] = {
        "available": google.is_available(),
        "models": GoogleProvider.list_models(),
        "default_model": GoogleProvider.DEFAULT_MODEL,
        "reason": None if google.is_available() else "GOOGLE_API_KEY not set",
    }

    # Check Ollama
    ollama = OllamaProvider()
    result["ollama"] = {
        "available": ollama.is_available(),
        "models": ollama.list_installed_models() if ollama.is_available() else [],
        "default_model": OllamaProvider.DEFAULT_MODEL,
        "reason": None if ollama.is_available() else "Ollama not running",
    }

    return result


def get_default_provider_info() -> dict:
    """Get info about the currently configured default provider."""
    provider_name = Config.LLM_PROVIDER
    model_name = Config.LLM_MODEL

    try:
        provider = get_provider(provider_name, model_name)
        return {
            "provider": provider_name,
            "model": provider.model,
            "available": provider.is_available(),
            "pricing": provider.get_pricing(),
        }
    except ValueError as e:
        return {
            "provider": provider_name,
            "model": model_name,
            "available": False,
            "error": str(e),
        }
