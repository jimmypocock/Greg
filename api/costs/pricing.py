"""
LLM pricing configuration.

Prices are in USD per 1 million tokens.
Updated: December 2025
"""

from decimal import Decimal
from typing import NamedTuple


class ModelPricing(NamedTuple):
    """Pricing for a specific model."""

    input_per_million: Decimal  # USD per 1M input tokens
    output_per_million: Decimal  # USD per 1M output tokens
    cached_per_million: Decimal | None = None  # USD per 1M cached tokens


# Pricing per model (USD per 1M tokens)
# Sources:
# - Anthropic: https://www.anthropic.com/pricing
# - OpenAI: https://openai.com/pricing
# - Google: https://ai.google.dev/pricing
MODEL_PRICING: dict[str, ModelPricing] = {
    # Anthropic Claude models
    "claude-3-5-sonnet-20241022": ModelPricing(
        input_per_million=Decimal("3.00"),
        output_per_million=Decimal("15.00"),
        cached_per_million=Decimal("0.30"),
    ),
    "claude-3-5-haiku-20241022": ModelPricing(
        input_per_million=Decimal("0.80"),
        output_per_million=Decimal("4.00"),
        cached_per_million=Decimal("0.08"),
    ),
    "claude-sonnet-4-20250514": ModelPricing(
        input_per_million=Decimal("3.00"),
        output_per_million=Decimal("15.00"),
        cached_per_million=Decimal("0.30"),
    ),
    "claude-3-opus-20240229": ModelPricing(
        input_per_million=Decimal("15.00"),
        output_per_million=Decimal("75.00"),
        cached_per_million=Decimal("1.50"),
    ),
    # OpenAI GPT-5 models (Dec 2025)
    "gpt-5.2": ModelPricing(
        input_per_million=Decimal("1.75"),
        output_per_million=Decimal("14.00"),
        cached_per_million=Decimal("0.175"),  # 90% cache discount
    ),
    "gpt-5.1": ModelPricing(
        input_per_million=Decimal("1.25"),
        output_per_million=Decimal("10.00"),
        cached_per_million=Decimal("0.125"),
    ),
    "gpt-5": ModelPricing(
        input_per_million=Decimal("1.25"),
        output_per_million=Decimal("10.00"),
        cached_per_million=Decimal("0.125"),
    ),
    "gpt-5-mini": ModelPricing(
        input_per_million=Decimal("0.25"),
        output_per_million=Decimal("2.00"),
        cached_per_million=Decimal("0.025"),
    ),
    "gpt-5-nano": ModelPricing(
        input_per_million=Decimal("0.05"),
        output_per_million=Decimal("0.40"),
        cached_per_million=Decimal("0.005"),
    ),
    # OpenAI GPT-4.1 models
    "gpt-4.1": ModelPricing(
        input_per_million=Decimal("2.00"),
        output_per_million=Decimal("8.00"),
        cached_per_million=Decimal("0.50"),
    ),
    "gpt-4.1-mini": ModelPricing(
        input_per_million=Decimal("0.40"),
        output_per_million=Decimal("1.60"),
        cached_per_million=Decimal("0.10"),
    ),
    "gpt-4.1-nano": ModelPricing(
        input_per_million=Decimal("0.10"),
        output_per_million=Decimal("0.40"),
        cached_per_million=Decimal("0.025"),
    ),
    # OpenAI GPT-4 models (legacy)
    "gpt-4o": ModelPricing(
        input_per_million=Decimal("2.50"),
        output_per_million=Decimal("10.00"),
        cached_per_million=Decimal("1.25"),
    ),
    "gpt-4o-mini": ModelPricing(
        input_per_million=Decimal("0.15"),
        output_per_million=Decimal("0.60"),
        cached_per_million=Decimal("0.075"),
    ),
    # OpenAI o-series reasoning models
    "o3-mini": ModelPricing(
        input_per_million=Decimal("1.10"),
        output_per_million=Decimal("4.40"),
    ),
    "o1": ModelPricing(
        input_per_million=Decimal("15.00"),
        output_per_million=Decimal("60.00"),
    ),
    "o1-mini": ModelPricing(
        input_per_million=Decimal("3.00"),
        output_per_million=Decimal("12.00"),
    ),
    # Google Gemini models
    "gemini-1.5-pro": ModelPricing(
        input_per_million=Decimal("1.25"),
        output_per_million=Decimal("5.00"),
    ),
    "gemini-1.5-flash": ModelPricing(
        input_per_million=Decimal("0.075"),
        output_per_million=Decimal("0.30"),
    ),
    "gemini-2.0-flash-exp": ModelPricing(
        input_per_million=Decimal("0.075"),
        output_per_million=Decimal("0.30"),
    ),
    # Ollama models (free - local)
    "mistral": ModelPricing(
        input_per_million=Decimal("0"),
        output_per_million=Decimal("0"),
    ),
    "llama3": ModelPricing(
        input_per_million=Decimal("0"),
        output_per_million=Decimal("0"),
    ),
    "llama3:8b": ModelPricing(
        input_per_million=Decimal("0"),
        output_per_million=Decimal("0"),
    ),
    "phi": ModelPricing(
        input_per_million=Decimal("0"),
        output_per_million=Decimal("0"),
    ),
    "deepseek": ModelPricing(
        input_per_million=Decimal("0"),
        output_per_million=Decimal("0"),
    ),
}

# Default pricing for unknown models (conservative estimate)
DEFAULT_PRICING = ModelPricing(
    input_per_million=Decimal("1.00"),
    output_per_million=Decimal("3.00"),
)


def get_model_pricing(model: str) -> ModelPricing:
    """
    Get pricing for a model.

    Args:
        model: Model name (e.g., 'gpt-4o', 'claude-3-5-sonnet-20241022')

    Returns:
        ModelPricing with input/output/cached costs per million tokens.
    """
    # Try exact match first
    if model in MODEL_PRICING:
        return MODEL_PRICING[model]

    # Try prefix matching for versioned models
    model_lower = model.lower()
    for known_model, pricing in MODEL_PRICING.items():
        if model_lower.startswith(known_model.lower()):
            return pricing

    # Return default for unknown models
    return DEFAULT_PRICING


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> tuple[Decimal, Decimal, Decimal]:
    """
    Calculate the cost for an LLM request.

    Args:
        model: Model name
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cached_tokens: Number of cached input tokens (Claude)

    Returns:
        Tuple of (input_cost, output_cost, total_cost) in USD.
    """
    pricing = get_model_pricing(model)

    # Calculate costs (price per million tokens)
    input_cost = (Decimal(input_tokens) / Decimal(1_000_000)) * pricing.input_per_million
    output_cost = (Decimal(output_tokens) / Decimal(1_000_000)) * pricing.output_per_million

    # Handle cached tokens (reduces input cost)
    if cached_tokens > 0 and pricing.cached_per_million is not None:
        cached_cost = (Decimal(cached_tokens) / Decimal(1_000_000)) * pricing.cached_per_million
        # Cached tokens are charged at cached rate instead of input rate
        input_cost -= (Decimal(cached_tokens) / Decimal(1_000_000)) * pricing.input_per_million
        input_cost += cached_cost

    total_cost = input_cost + output_cost

    return input_cost, output_cost, total_cost
