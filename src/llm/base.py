"""
Abstract base class for LLM providers.

All providers (Anthropic, OpenAI, Google, Ollama) implement this interface.
This ensures consistent behavior and easy swapping between providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Generator, Optional
from datetime import datetime


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""

    content: str
    provider: str  # "anthropic", "openai", "google", "ollama"
    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    latency_ms: int
    cost_usd: float
    input_cost_usd: float = 0.0
    output_cost_usd: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    cached_tokens: int = 0  # For prompt caching (Anthropic, Google)
    raw_response: Optional[dict] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "content": self.content,
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "cost_usd": self.cost_usd,
            "input_cost_usd": self.input_cost_usd,
            "output_cost_usd": self.output_cost_usd,
            "timestamp": self.timestamp,
            "cached_tokens": self.cached_tokens,
        }


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    # Subclasses should set these
    PROVIDER_NAME: str = "base"
    DEFAULT_MODEL: str = ""

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ):
        self.model = model or self.DEFAULT_MODEL
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            prompt: The user prompt/question
            system_prompt: Optional system instructions
            **kwargs: Provider-specific options (temperature, max_tokens, etc.)

        Returns:
            LLMResponse with content and metadata
        """
        pass

    @abstractmethod
    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Generator[str, None, Optional[LLMResponse]]:
        """
        Generate a streaming response.

        Yields text chunks as they arrive.
        After iteration completes, the generator returns an LLMResponse
        with the full content and metadata.

        Args:
            prompt: The user prompt/question
            system_prompt: Optional system instructions

        Yields:
            Text chunks as they arrive

        Returns:
            LLMResponse with full content and metadata (access via .send(None) or
            catch StopIteration)
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available (API key set, service reachable)."""
        pass

    @abstractmethod
    def get_pricing(self) -> dict[str, float]:
        """
        Get pricing for the current model.

        Returns:
            Dict with 'input' and 'output' costs per 1M tokens in USD
        """
        pass

    def calculate_cost(self, input_tokens: int, output_tokens: int) -> tuple[float, float, float]:
        """
        Calculate cost for a request.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Tuple of (input_cost, output_cost, total_cost) in USD
        """
        pricing = self.get_pricing()
        input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0)
        output_cost = (output_tokens / 1_000_000) * pricing.get("output", 0)
        return input_cost, output_cost, input_cost + output_cost

    def get_model_info(self) -> dict:
        """Get information about the current model configuration."""
        return {
            "provider": self.PROVIDER_NAME,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "available": self.is_available(),
            "pricing": self.get_pricing(),
        }
