"""
OpenAI LLM provider.

Supports GPT-4o, GPT-4o-mini, GPT-4 Turbo, and GPT-3.5 Turbo.
"""

import os
import time
from typing import Generator, Optional

import openai

from .base import BaseLLMProvider, LLMResponse


# Pricing per 1M tokens (as of Dec 2025)
OPENAI_PRICING = {
    # GPT-4o family
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-2024-11-20": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
    # GPT-4 Turbo
    "gpt-4-turbo": {"input": 10.00, "output": 30.00},
    "gpt-4-turbo-preview": {"input": 10.00, "output": 30.00},
    # GPT-4
    "gpt-4": {"input": 30.00, "output": 60.00},
    # GPT-3.5
    "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
    "gpt-3.5-turbo-0125": {"input": 0.50, "output": 1.50},
    # o1 reasoning models
    "o1-preview": {"input": 15.00, "output": 60.00},
    "o1-mini": {"input": 3.00, "output": 12.00},
}

# Model aliases
MODEL_ALIASES = {
    "gpt4": "gpt-4o",
    "gpt-4": "gpt-4o",
    "gpt4o": "gpt-4o",
    "gpt4-mini": "gpt-4o-mini",
    "gpt-4-mini": "gpt-4o-mini",
    "gpt35": "gpt-3.5-turbo",
    "gpt-3.5": "gpt-3.5-turbo",
}


class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT provider."""

    PROVIDER_NAME = "openai"
    DEFAULT_MODEL = "gpt-4o-mini"  # Good balance of cost/quality

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        api_key: Optional[str] = None,
    ):
        # Resolve model alias
        resolved_model = MODEL_ALIASES.get(model, model) if model else None
        super().__init__(resolved_model, temperature, max_tokens)

        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = None

        if self.api_key:
            self.client = openai.OpenAI(api_key=self.api_key)

    def is_available(self) -> bool:
        """Check if OpenAI API is available."""
        return self.client is not None and bool(self.api_key)

    def get_pricing(self) -> dict[str, float]:
        """Get pricing for the current model."""
        return OPENAI_PRICING.get(
            self.model,
            {"input": 2.50, "output": 10.00},  # Default to GPT-4o pricing
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a response from OpenAI."""
        if not self.client:
            raise ValueError("OpenAI client not initialized. Set OPENAI_API_KEY.")

        start_time = time.time()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_completion_tokens=kwargs.get("max_tokens", self.max_tokens),
            temperature=kwargs.get("temperature", self.temperature),
        )

        latency_ms = int((time.time() - start_time) * 1000)

        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        cached_tokens = getattr(response.usage, "prompt_tokens_details", {})
        cached_tokens = getattr(cached_tokens, "cached_tokens", 0) if cached_tokens else 0

        input_cost, output_cost, total_cost = self.calculate_cost(input_tokens, output_tokens)

        return LLMResponse(
            content=response.choices[0].message.content,
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
                "finish_reason": response.choices[0].finish_reason,
            },
        )

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Generator[str, None, Optional[LLMResponse]]:
        """Generate a streaming response from OpenAI."""
        if not self.client:
            raise ValueError("OpenAI client not initialized. Set OPENAI_API_KEY.")

        start_time = time.time()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_completion_tokens=kwargs.get("max_tokens", self.max_tokens),
            temperature=kwargs.get("temperature", self.temperature),
            stream=True,
            stream_options={"include_usage": True},
        )

        full_content = ""
        input_tokens = 0
        output_tokens = 0

        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                text = chunk.choices[0].delta.content
                full_content += text
                yield text

            # Get usage from final chunk
            if chunk.usage:
                input_tokens = chunk.usage.prompt_tokens
                output_tokens = chunk.usage.completion_tokens

        latency_ms = int((time.time() - start_time) * 1000)

        # If streaming didn't provide usage, estimate
        if input_tokens == 0:
            # Rough estimate: 4 chars per token
            input_tokens = len(prompt) // 4
            output_tokens = len(full_content) // 4

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
        )

    @staticmethod
    def list_models() -> list[str]:
        """List available OpenAI models."""
        return list(OPENAI_PRICING.keys())
