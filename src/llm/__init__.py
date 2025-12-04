"""
LLM Provider Module

Provides a unified interface for multiple LLM providers:
- Anthropic (Claude)
- OpenAI (GPT)
- Google (Gemini)
- Ollama (Local models)

Usage:
    from src.llm import get_provider, get_available_providers, LLMResponse

    # Get provider (uses .env defaults or specify at runtime)
    llm = get_provider()  # Default from .env
    llm = get_provider("anthropic", model="claude-3-5-haiku")

    # Generate response
    response = llm.generate(
        prompt="What is machine learning?",
        system_prompt="You are a helpful assistant."
    )

    print(response.content)
    print(f"Cost: ${response.cost_usd:.4f}")
    print(f"Tokens: {response.total_tokens}")

    # Streaming
    for chunk in llm.generate_stream(prompt="Explain RAG"):
        print(chunk, end="", flush=True)

    # Check available providers
    providers = get_available_providers()
    for name, info in providers.items():
        status = "" if info["available"] else ""
        print(f"{status} {name}: {info.get('reason', 'Ready')}")
"""

from .base import BaseLLMProvider, LLMResponse
from .factory import get_provider, get_available_providers, get_default_provider_info
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAIProvider
from .google_provider import GoogleProvider
from .ollama_provider import OllamaProvider

__all__ = [
    # Core
    "BaseLLMProvider",
    "LLMResponse",
    # Factory
    "get_provider",
    "get_available_providers",
    "get_default_provider_info",
    # Providers
    "AnthropicProvider",
    "OpenAIProvider",
    "GoogleProvider",
    "OllamaProvider",
]
