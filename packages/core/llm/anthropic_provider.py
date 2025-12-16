"""
Anthropic Claude LLM provider.

Supports Claude 3.5 Sonnet, Claude 3.5 Haiku, and Claude 3 Opus.
"""

import os
import time
from typing import Generator, Optional

import anthropic

from .base import BaseLLMProvider, LLMResponse


# Pricing per 1M tokens (as of Dec 2025)
ANTHROPIC_PRICING = {
    # Claude 4 / Sonnet 4
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00},
    # Claude 3.5 family
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00},
    # Claude 3 family
    "claude-3-opus-20240229": {"input": 15.00, "output": 75.00},
    "claude-3-sonnet-20240229": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}

# Model aliases for convenience
MODEL_ALIASES = {
    "claude-4": "claude-sonnet-4-20250514",
    "claude-sonnet": "claude-sonnet-4-20250514",
    "claude-3.5-sonnet": "claude-3-5-sonnet-20241022",
    "claude-3.5-haiku": "claude-3-5-haiku-20241022",
    "claude-haiku": "claude-3-5-haiku-20241022",
    "claude-opus": "claude-3-opus-20240229",
}


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider."""

    PROVIDER_NAME = "anthropic"
    DEFAULT_MODEL = "claude-3-5-haiku-20241022"  # Good balance of cost/quality

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        api_key: Optional[str] = None,
    ):
        # Resolve model alias if used
        resolved_model = MODEL_ALIASES.get(model, model) if model else None
        super().__init__(resolved_model, temperature, max_tokens)

        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = None

        if self.api_key:
            self.client = anthropic.Anthropic(api_key=self.api_key)

    def is_available(self) -> bool:
        """Check if Anthropic API is available."""
        return self.client is not None and bool(self.api_key)

    def get_pricing(self) -> dict[str, float]:
        """Get pricing for the current model."""
        return ANTHROPIC_PRICING.get(
            self.model,
            {"input": 3.00, "output": 15.00},  # Default to Sonnet pricing
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a response from Claude."""
        if not self.client:
            raise ValueError("Anthropic client not initialized. Set ANTHROPIC_API_KEY.")

        start_time = time.time()

        # Build request
        request_kwargs = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            request_kwargs["system"] = system_prompt

        # Make request
        response = self.client.messages.create(**request_kwargs)

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract token counts
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        cached_tokens = getattr(response.usage, "cache_read_input_tokens", 0) or 0

        # Calculate costs
        input_cost, output_cost, total_cost = self.calculate_cost(input_tokens, output_tokens)

        return LLMResponse(
            content=response.content[0].text,
            provider=self.PROVIDER_NAME,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            latency_ms=latency_ms,
            cost_usd=total_cost,
            input_cost_usd=input_cost,
            output_cost_usd=output_cost,
            cached_tokens=cached_tokens,
            raw_response={
                "id": response.id,
                "stop_reason": response.stop_reason,
            },
        )

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Generator[str, None, Optional[LLMResponse]]:
        """Generate a streaming response from Claude."""
        if not self.client:
            raise ValueError("Anthropic client not initialized. Set ANTHROPIC_API_KEY.")

        start_time = time.time()

        request_kwargs = {
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "messages": [{"role": "user", "content": prompt}],
        }

        if system_prompt:
            request_kwargs["system"] = system_prompt

        full_content = ""
        input_tokens = 0
        output_tokens = 0
        cached_tokens = 0

        with self.client.messages.stream(**request_kwargs) as stream:
            for text in stream.text_stream:
                full_content += text
                yield text

            # Get final message for token counts
            final_message = stream.get_final_message()
            input_tokens = final_message.usage.input_tokens
            output_tokens = final_message.usage.output_tokens
            cached_tokens = getattr(final_message.usage, "cache_read_input_tokens", 0) or 0

        latency_ms = int((time.time() - start_time) * 1000)
        input_cost, output_cost, total_cost = self.calculate_cost(input_tokens, output_tokens)

        return LLMResponse(
            content=full_content,
            provider=self.PROVIDER_NAME,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            latency_ms=latency_ms,
            cost_usd=total_cost,
            input_cost_usd=input_cost,
            output_cost_usd=output_cost,
            cached_tokens=cached_tokens,
        )

    @staticmethod
    def list_models() -> list[str]:
        """List available Claude models."""
        return list(ANTHROPIC_PRICING.keys())
