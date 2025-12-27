"""
Google Gemini LLM provider.

Uses the new google-genai SDK (replacement for google-generativeai).
Supports Gemini 2.0, 1.5 Pro, and 1.5 Flash models.
"""

import os
import time
from typing import Generator, Optional

from google import genai
from google.genai import types

from .base import BaseLLMProvider, LLMResponse


# Pricing per 1M tokens (as of Dec 2025)
# Note: Gemini has different pricing for prompts <= 128K and > 128K
GOOGLE_PRICING = {
    # Gemini 2.0
    "gemini-2.0-flash-exp": {"input": 0.0, "output": 0.0},  # Free during preview
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40},
    # Gemini 1.5
    "gemini-1.5-pro": {"input": 1.25, "output": 5.00},
    "gemini-1.5-pro-latest": {"input": 1.25, "output": 5.00},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash-latest": {"input": 0.075, "output": 0.30},
    "gemini-1.5-flash-8b": {"input": 0.0375, "output": 0.15},
    # Gemini 1.0
    "gemini-1.0-pro": {"input": 0.50, "output": 1.50},
    "gemini-pro": {"input": 0.50, "output": 1.50},
}

# Model aliases
MODEL_ALIASES = {
    "gemini": "gemini-1.5-flash",
    "gemini-flash": "gemini-1.5-flash",
    "gemini-pro": "gemini-1.5-pro",
    "gemini-2": "gemini-2.0-flash-exp",
    "gemini-2.0": "gemini-2.0-flash-exp",
}


class GoogleProvider(BaseLLMProvider):
    """Google Gemini provider using google-genai SDK."""

    PROVIDER_NAME = "google"
    DEFAULT_MODEL = "gemini-1.5-flash"  # Fast and cheap

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

        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.client = None

        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)

    def is_available(self) -> bool:
        """Check if Google API is available."""
        return self.client is not None and bool(self.api_key)

    def get_pricing(self) -> dict[str, float]:
        """Get pricing for the current model."""
        return GOOGLE_PRICING.get(
            self.model,
            {"input": 0.075, "output": 0.30},  # Default to Flash pricing
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a response from Gemini."""
        if not self.client:
            raise ValueError("Google client not initialized. Set GOOGLE_API_KEY.")

        start_time = time.time()

        # Build config
        config = types.GenerateContentConfig(
            temperature=kwargs.get("temperature", self.temperature),
            max_output_tokens=kwargs.get("max_tokens", self.max_tokens),
        )

        if system_prompt:
            config.system_instruction = system_prompt

        # Make request
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract token counts from usage metadata
        usage = response.usage_metadata
        input_tokens = usage.prompt_token_count if usage else 0
        output_tokens = usage.candidates_token_count if usage else 0
        cached_tokens = usage.cached_content_token_count if usage else 0

        input_cost, output_cost, total_cost = self.calculate_cost(input_tokens, output_tokens)

        return LLMResponse(
            content=response.text,
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

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Generator[str, None, Optional[LLMResponse]]:
        """Generate a streaming response from Gemini."""
        if not self.client:
            raise ValueError("Google client not initialized. Set GOOGLE_API_KEY.")

        start_time = time.time()

        config = types.GenerateContentConfig(
            temperature=kwargs.get("temperature", self.temperature),
            max_output_tokens=kwargs.get("max_tokens", self.max_tokens),
        )

        if system_prompt:
            config.system_instruction = system_prompt

        full_content = ""
        input_tokens = 0
        output_tokens = 0
        cached_tokens = 0

        # Stream response
        for chunk in self.client.models.generate_content_stream(
            model=self.model,
            contents=prompt,
            config=config,
        ):
            if chunk.text:
                full_content += chunk.text
                yield chunk.text

            # Get usage from chunks
            if chunk.usage_metadata:
                input_tokens = chunk.usage_metadata.prompt_token_count or input_tokens
                output_tokens = chunk.usage_metadata.candidates_token_count or output_tokens
                cached_tokens = chunk.usage_metadata.cached_content_token_count or cached_tokens

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
        """List available Gemini models."""
        return list(GOOGLE_PRICING.keys())
