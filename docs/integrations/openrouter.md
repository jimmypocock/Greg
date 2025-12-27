# OpenRouter Integration

> **Status:** Future Consideration
> **Priority:** Medium (useful for scaling/optimization)
> **Website:** [openrouter.ai](https://openrouter.ai)

## Overview

OpenRouter is a unified API gateway that provides access to 200+ LLM models from multiple providers through a single API endpoint. It acts as a router/proxy, allowing you to switch between models without changing your code.

```
Your App → OpenRouter API → Anthropic / OpenAI / Google / Meta / Mistral / etc.
```

## Why Use OpenRouter?

### Benefits

| Benefit | Description |
|---------|-------------|
| **Single API** | One integration for all providers |
| **Unified billing** | One dashboard, one invoice |
| **Model fallback** | Automatic failover if a provider is down |
| **Easy experimentation** | Try new models without new integrations |
| **Cost optimization** | Route tasks to cost-appropriate models |
| **No vendor lock-in** | Switch models with a config change |

### Trade-offs

| Consideration | Impact |
|---------------|--------|
| **Added latency** | ~50-100ms additional hop |
| **Dependency** | Another service in your stack |
| **Pricing markup** | Small margin on top of provider costs |
| **Support** | Issues may require coordinating with OpenRouter + provider |

## Available Models

OpenRouter provides access to models from:

- **Anthropic**: Claude Opus, Sonnet, Haiku
- **OpenAI**: GPT-4o, GPT-4 Turbo, GPT-3.5
- **Google**: Gemini Pro, Gemini Flash
- **Meta**: Llama 3.1 (70B, 8B)
- **Mistral**: Mistral Large, Medium, Small
- **Others**: Cohere, AI21, Perplexity, and 150+ more

### Model Selection: Latency vs Throughput

> Data from [State of AI Coding 2025](https://www.greptile.com/state-of-ai-coding-2025)

Different models excel at different use cases:

| Metric | Anthropic (Claude) | OpenAI (GPT) | Best For |
|--------|-------------------|--------------|----------|
| **First Token Latency** | <2.5s (p50) | >5s | Interactive chat, real-time co-writing |
| **Throughput** | 14-21 tok/s | 53-73 tok/s | Batch processing, long generation |

**Practical Guidance for Songwriter App:**

```python
# Interactive features → Anthropic (low latency)
INTERACTIVE_MODEL = "anthropic/claude-sonnet-4"  # Fast first response

# Batch/background features → OpenAI (high throughput)
BATCH_MODEL = "openai/gpt-4o"  # More tokens per second

# Route by use case
TASK_MODEL_MAP = {
    # Interactive (latency matters)
    "chat": "anthropic/claude-sonnet-4",
    "quick_rhyme": "anthropic/claude-haiku",
    "realtime_suggestion": "anthropic/claude-sonnet-4",

    # Batch (throughput matters)
    "full_song_critique": "openai/gpt-4o",
    "album_analysis": "openai/gpt-4o",
    "bulk_export": "openai/gpt-4o",
}
```

## Use Cases for Songwriter App

### 1. Model A/B Testing for AI Critic

Compare critique quality across different models:

```python
CRITIC_MODELS = {
    "claude": "anthropic/claude-sonnet-4",
    "gpt4": "openai/gpt-4o",
    "gemini": "google/gemini-pro-1.5",
}

async def get_critique(song: Song, model_key: str = "claude") -> Critique:
    model = CRITIC_MODELS[model_key]

    response = await openrouter.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": CRITIC_SYSTEM_PROMPT},
            {"role": "user", "content": format_song_for_critique(song)},
        ],
    )

    return parse_critique(response)

# A/B test in production
async def critique_with_ab_test(song: Song, user: User) -> Critique:
    # 80% Claude, 10% GPT-4, 10% Gemini
    model_key = random.choices(
        ["claude", "gpt4", "gemini"],
        weights=[0.8, 0.1, 0.1]
    )[0]

    critique = await get_critique(song, model_key)

    # Log for analysis
    await log_critique_model(user.id, song.id, model_key)

    return critique
```

### 2. Cost-Tiered Task Routing

Route tasks to cost-appropriate models:

```python
# Model pricing tiers (approximate $/1M tokens)
MODEL_TIERS = {
    "cheap": {
        "model": "meta-llama/llama-3.1-8b-instruct",
        "input_cost": 0.05,
        "use_for": ["classification", "simple_extraction"],
    },
    "standard": {
        "model": "anthropic/claude-sonnet-4",
        "input_cost": 3.00,
        "use_for": ["critique", "suggestions", "chat"],
    },
    "premium": {
        "model": "anthropic/claude-opus-4",
        "input_cost": 15.00,
        "use_for": ["deep_analysis", "complex_generation"],
    },
}

async def classify_mood(text: str) -> str:
    """Simple task → cheap model."""
    response = await openrouter.chat.completions.create(
        model=MODEL_TIERS["cheap"]["model"],
        messages=[{"role": "user", "content": f"Classify mood: {text}"}],
    )
    return response.choices[0].message.content

async def generate_critique(song: Song) -> Critique:
    """Standard task → standard model."""
    response = await openrouter.chat.completions.create(
        model=MODEL_TIERS["standard"]["model"],
        messages=[...],
    )
    return parse_critique(response)

async def deep_song_analysis(song: Song) -> Analysis:
    """Complex task → premium model."""
    response = await openrouter.chat.completions.create(
        model=MODEL_TIERS["premium"]["model"],
        messages=[...],
    )
    return parse_analysis(response)
```

### 3. Automatic Failover

Handle provider outages gracefully:

```python
FALLBACK_CHAIN = [
    "anthropic/claude-sonnet-4",
    "openai/gpt-4o",
    "google/gemini-pro-1.5",
]

async def robust_completion(messages: list[dict], **kwargs) -> str:
    last_error = None

    for model in FALLBACK_CHAIN:
        try:
            response = await openrouter.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )
            return response.choices[0].message.content

        except Exception as e:
            logger.warning(f"Model {model} failed: {e}")
            last_error = e
            continue

    raise last_error  # All models failed
```

### 4. User Model Preferences

Let users choose their preferred AI model:

```python
# User preferences schema
class UserPreferences(BaseModel):
    preferred_model: str = "anthropic/claude-sonnet-4"

# Available models for users to choose
USER_SELECTABLE_MODELS = [
    {"id": "anthropic/claude-sonnet-4", "name": "Claude Sonnet", "tier": "standard"},
    {"id": "anthropic/claude-opus-4", "name": "Claude Opus", "tier": "premium"},
    {"id": "openai/gpt-4o", "name": "GPT-4o", "tier": "standard"},
    {"id": "google/gemini-pro-1.5", "name": "Gemini Pro", "tier": "standard"},
]

async def get_ai_response(user: User, messages: list[dict]) -> str:
    model = user.preferences.get("preferred_model", "anthropic/claude-sonnet-4")

    response = await openrouter.chat.completions.create(
        model=model,
        messages=messages,
    )

    return response.choices[0].message.content
```

### 5. Specialized Models for Specific Tasks

Use domain-optimized models:

```python
TASK_MODELS = {
    # Creative writing tasks
    "lyric_generation": "anthropic/claude-sonnet-4",

    # Fast classification
    "mood_detection": "meta-llama/llama-3.1-8b-instruct",

    # Code generation (for any tooling)
    "code_tasks": "anthropic/claude-sonnet-4",

    # Long context (full song analysis)
    "long_analysis": "google/gemini-pro-1.5",  # 1M context window

    # Embedding generation
    "embeddings": "openai/text-embedding-3-small",
}

async def analyze_full_album(songs: list[Song]) -> AlbumAnalysis:
    """Use long-context model for album-wide analysis."""
    full_text = "\n\n---\n\n".join(format_song(s) for s in songs)

    response = await openrouter.chat.completions.create(
        model=TASK_MODELS["long_analysis"],
        messages=[
            {"role": "system", "content": ALBUM_ANALYSIS_PROMPT},
            {"role": "user", "content": full_text},
        ],
    )

    return parse_album_analysis(response)
```

---

## Implementation

### Installation

```bash
# OpenRouter uses OpenAI-compatible API
uv add openai
```

### Configuration

```python
# api/config/settings.py

class Settings(BaseSettings):
    # OpenRouter
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # Default model
    default_llm_model: str = "anthropic/claude-sonnet-4"

    # Fallback chain
    llm_fallback_models: list[str] = [
        "anthropic/claude-sonnet-4",
        "openai/gpt-4o",
    ]
```

```bash
# .env
OPENROUTER_API_KEY=sk-or-v1-xxxx
DEFAULT_LLM_MODEL=anthropic/claude-sonnet-4
```

### Client Setup

```python
# api/llm/openrouter.py

from openai import AsyncOpenAI
from api.config import settings

def get_openrouter_client() -> AsyncOpenAI:
    """Get OpenRouter client (OpenAI-compatible)."""
    return AsyncOpenAI(
        base_url=settings.openrouter_base_url,
        api_key=settings.openrouter_api_key,
        default_headers={
            "HTTP-Referer": "https://yourapp.com",  # Required by OpenRouter
            "X-Title": "Songwriter App",  # Shows in OpenRouter dashboard
        },
    )

openrouter = get_openrouter_client()
```

### Provider Abstraction

Create a provider-agnostic interface:

```python
# api/llm/provider.py

from abc import ABC, abstractmethod
from typing import AsyncIterator

class LLMProvider(ABC):
    @abstractmethod
    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        **kwargs,
    ) -> str:
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        model: str | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        pass


class OpenRouterProvider(LLMProvider):
    def __init__(self):
        self.client = get_openrouter_client()
        self.default_model = settings.default_llm_model

    async def complete(
        self,
        messages: list[dict],
        model: str | None = None,
        **kwargs,
    ) -> str:
        response = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            **kwargs,
        )
        return response.choices[0].message.content

    async def stream(
        self,
        messages: list[dict],
        model: str | None = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        response = await self.client.chat.completions.create(
            model=model or self.default_model,
            messages=messages,
            stream=True,
            **kwargs,
        )

        async for chunk in response:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content


class OllamaProvider(LLMProvider):
    """Keep Ollama as local fallback."""

    async def complete(self, messages: list[dict], model: str | None = None, **kwargs) -> str:
        # Existing Ollama implementation
        ...


# Factory
def get_llm_provider() -> LLMProvider:
    if settings.openrouter_api_key:
        return OpenRouterProvider()
    return OllamaProvider()
```

### Cost Tracking

Track costs per model:

```python
# api/llm/cost_tracker.py

# OpenRouter returns usage in response
async def complete_with_tracking(
    user_id: UUID,
    messages: list[dict],
    model: str,
    task_type: str,
) -> tuple[str, dict]:
    response = await openrouter.chat.completions.create(
        model=model,
        messages=messages,
    )

    # Extract usage
    usage = response.usage

    # Log to database
    await log_ai_request(
        user_id=user_id,
        model=model,
        task_type=task_type,
        input_tokens=usage.prompt_tokens,
        output_tokens=usage.completion_tokens,
        cost=calculate_cost(model, usage),
    )

    return response.choices[0].message.content, {
        "model": model,
        "tokens": usage.prompt_tokens + usage.completion_tokens,
    }
```

---

## Migration Path

### Phase 1: Add OpenRouter as Alternative

Keep existing direct integrations, add OpenRouter as option:

```python
LLM_BACKEND = os.getenv("LLM_BACKEND", "direct")  # "direct" or "openrouter"

def get_provider():
    if LLM_BACKEND == "openrouter":
        return OpenRouterProvider()
    return DirectAnthropicProvider()  # Current implementation
```

### Phase 2: A/B Test Quality

Run both backends, compare outputs:

```python
async def critique_with_comparison(song: Song) -> Critique:
    # Get critiques from both
    direct_critique = await direct_provider.critique(song)
    openrouter_critique = await openrouter_provider.critique(song)

    # Log for comparison
    await log_comparison(song.id, direct_critique, openrouter_critique)

    # Return primary
    return direct_critique
```

### Phase 3: Full Migration

Once validated, switch entirely to OpenRouter:

```python
# Remove direct provider code
# Update all LLM calls to use OpenRouter
# Update cost tracking for OpenRouter pricing
```

---

## API Reference

### Chat Completions

```python
response = await openrouter.chat.completions.create(
    model="anthropic/claude-sonnet-4",
    messages=[
        {"role": "system", "content": "You are a songwriting assistant."},
        {"role": "user", "content": "Help me write a chorus about..."},
    ],
    max_tokens=1000,
    temperature=0.7,
    stream=False,
)

content = response.choices[0].message.content
```

### Streaming

```python
stream = await openrouter.chat.completions.create(
    model="anthropic/claude-sonnet-4",
    messages=[...],
    stream=True,
)

async for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

### Model Listing

```python
# Get available models
import httpx

async def list_models():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://openrouter.ai/api/v1/models",
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
        )
        return response.json()["data"]
```

### Credit Balance

```python
async def get_credits():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://openrouter.ai/api/v1/auth/key",
            headers={"Authorization": f"Bearer {settings.openrouter_api_key}"},
        )
        data = response.json()
        return {
            "credits": data["data"]["limit"],
            "usage": data["data"]["usage"],
            "remaining": data["data"]["limit"] - data["data"]["usage"],
        }
```

---

## Monitoring & Observability

### Dashboard

OpenRouter provides a dashboard at [openrouter.ai/activity](https://openrouter.ai/activity) showing:

- Request volume by model
- Token usage and costs
- Error rates
- Latency percentiles

### Custom Logging

```python
import structlog

logger = structlog.get_logger()

async def logged_completion(messages: list[dict], model: str, **kwargs) -> str:
    start = time.time()

    try:
        response = await openrouter.chat.completions.create(
            model=model,
            messages=messages,
            **kwargs,
        )

        latency = time.time() - start

        logger.info(
            "llm_request",
            model=model,
            latency_ms=latency * 1000,
            input_tokens=response.usage.prompt_tokens,
            output_tokens=response.usage.completion_tokens,
        )

        return response.choices[0].message.content

    except Exception as e:
        logger.error("llm_request_failed", model=model, error=str(e))
        raise
```

---

## Security Considerations

### API Key Management

```python
# Never log API keys
# Use environment variables
# Rotate keys periodically

# Rate limit by user to prevent abuse
@limiter.limit("50/minute")
async def ai_endpoint(user: CurrentUser):
    ...
```

### Content Filtering

OpenRouter passes content through without filtering. Implement your own:

```python
async def safe_completion(messages: list[dict], **kwargs) -> str:
    # Pre-filter input
    for msg in messages:
        if contains_prohibited_content(msg["content"]):
            raise ValueError("Prohibited content detected")

    response = await openrouter.chat.completions.create(...)

    # Post-filter output
    content = response.choices[0].message.content
    if contains_prohibited_content(content):
        return "[Content filtered]"

    return content
```

---

## Cost Comparison

Approximate pricing (as of 2024, verify current rates):

| Model | Direct Price | OpenRouter Price | Markup |
|-------|--------------|------------------|--------|
| Claude Sonnet | $3/$15 per 1M | $3/$15 per 1M | ~0% |
| GPT-4o | $5/$15 per 1M | $5/$15 per 1M | ~0% |
| Llama 3.1 70B | N/A (self-host) | $0.50/$0.75 per 1M | N/A |
| Gemini Pro | $1.25/$5 per 1M | $1.25/$5 per 1M | ~0% |

OpenRouter generally matches provider pricing with minimal markup.

---

## Recommendation

### When to Adopt

- **Now:** If you want to experiment with multiple models
- **Soon:** When you need production redundancy/failover
- **Later:** If current single-provider setup works fine

### Suggested Approach

1. **Keep Ollama** for local development (free, fast iteration)
2. **Add OpenRouter** for production cloud LLM access
3. **Use model routing** based on task complexity and cost
4. **Monitor costs** and optimize model selection over time

---

## References

- [OpenRouter Documentation](https://openrouter.ai/docs)
- [OpenRouter Models](https://openrouter.ai/models)
- [OpenRouter Pricing](https://openrouter.ai/docs/models)
- [Claude Code Integration Guide](https://openrouter.ai/docs/guides/claude-code-integration)
