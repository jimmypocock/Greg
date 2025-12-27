"""
Ollama LLM provider for local models.

Supports any model installed via Ollama (Mistral, Llama, Phi, etc.).
Local models are free to run.
"""

import time
from typing import Generator, Optional

import ollama

from api.config import Config

from .base import BaseLLMProvider, LLMResponse


class OllamaProvider(BaseLLMProvider):
    """Ollama provider for local LLMs."""

    PROVIDER_NAME = "ollama"
    DEFAULT_MODEL = "mistral"

    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        host: Optional[str] = None,
    ):
        super().__init__(model, temperature, max_tokens)
        self.host = host or Config.OLLAMA_HOST
        self.client = ollama.Client(host=self.host)

    def is_available(self) -> bool:
        """Check if Ollama is running and model is available."""
        try:
            # Check if Ollama is running
            models = self.client.list()
            if not models:
                return False

            # Check if our model is available
            model_names = [m.get("name", "").split(":")[0] for m in models.get("models", [])]
            return self.model in model_names or f"{self.model}:latest" in [
                m.get("name", "") for m in models.get("models", [])
            ]
        except Exception:
            return False

    def get_pricing(self) -> dict[str, float]:
        """Local models are free."""
        return {"input": 0.0, "output": 0.0}

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a response from Ollama."""
        start_time = time.time()

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # Make request
        response = self.client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            },
        )

        latency_ms = int((time.time() - start_time) * 1000)

        # Extract token counts
        input_tokens = response.get("prompt_eval_count", 0)
        output_tokens = response.get("eval_count", 0)

        return LLMResponse(
            content=response["message"]["content"],
            provider=self.PROVIDER_NAME,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            latency_ms=latency_ms,
            cost_usd=0.0,  # Free!
            input_cost_usd=0.0,
            output_cost_usd=0.0,
            raw_response={
                "model": response.get("model"),
                "done_reason": response.get("done_reason"),
            },
        )

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs,
    ) -> Generator[str, None, Optional[LLMResponse]]:
        """Generate a streaming response from Ollama."""
        start_time = time.time()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        full_content = ""
        input_tokens = 0
        output_tokens = 0

        # Stream response
        stream = self.client.chat(
            model=self.model,
            messages=messages,
            options={
                "temperature": kwargs.get("temperature", self.temperature),
                "num_predict": kwargs.get("max_tokens", self.max_tokens),
            },
            stream=True,
        )

        for chunk in stream:
            if chunk.get("message", {}).get("content"):
                text = chunk["message"]["content"]
                full_content += text
                yield text

            # Get token counts from final chunk
            if chunk.get("done"):
                input_tokens = chunk.get("prompt_eval_count", 0)
                output_tokens = chunk.get("eval_count", 0)

        latency_ms = int((time.time() - start_time) * 1000)

        return LLMResponse(
            content=full_content,
            provider=self.PROVIDER_NAME,
            model=self.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            latency_ms=latency_ms,
            cost_usd=0.0,
            input_cost_usd=0.0,
            output_cost_usd=0.0,
        )

    def list_installed_models(self) -> list[str]:
        """List models installed in Ollama."""
        try:
            response = self.client.list()
            return [m.get("name", "") for m in response.get("models", [])]
        except Exception:
            return []

    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry."""
        try:
            self.client.pull(model_name)
            return True
        except Exception:
            return False
