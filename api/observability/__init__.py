"""
LangSmith Observability Integration.

Provides tracing, logging, and monitoring for LLM calls.

Setup:
    1. Create account at smith.langchain.com
    2. Set LANGSMITH_API_KEY in .env
    3. Tracing is auto-enabled when API key is present

Usage:
    from api.observability import traceable, get_langsmith_client

    @traceable(name="my-operation")
    def my_function():
        ...

    # Or wrap OpenAI/Anthropic clients
    from api.observability import wrap_openai_client, wrap_anthropic_client
    client = wrap_openai_client(OpenAI())
"""

import os
import logging
from functools import wraps
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger(__name__)

# Check if LangSmith is configured
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "greg")
LANGSMITH_ENABLED = bool(LANGSMITH_API_KEY)

# Set environment variables for LangSmith SDK
if LANGSMITH_ENABLED:
    os.environ["LANGSMITH_TRACING"] = "true"
    os.environ["LANGSMITH_PROJECT"] = LANGSMITH_PROJECT
    logger.info(f"LangSmith tracing enabled for project: {LANGSMITH_PROJECT}")
else:
    os.environ["LANGSMITH_TRACING"] = "false"
    logger.debug("LangSmith tracing disabled (LANGSMITH_API_KEY not set)")

# Type variable for generic function wrapping
F = TypeVar("F", bound=Callable[..., Any])


def get_langsmith_client():
    """Get LangSmith client for direct API access."""
    if not LANGSMITH_ENABLED:
        return None

    try:
        from langsmith import Client
        return Client()
    except Exception as e:
        logger.warning(f"Failed to create LangSmith client: {e}")
        return None


def traceable(
    name: Optional[str] = None,
    run_type: str = "chain",
    metadata: Optional[dict] = None,
) -> Callable[[F], F]:
    """
    Decorator to trace function execution in LangSmith.

    Args:
        name: Name for the trace (defaults to function name)
        run_type: Type of run ("chain", "llm", "tool", "retriever")
        metadata: Additional metadata to attach to the trace

    Usage:
        @traceable(name="analyze-song")
        async def analyze_song(song_id: str):
            ...
    """
    def decorator(func: F) -> F:
        if not LANGSMITH_ENABLED:
            return func

        try:
            from langsmith import traceable as ls_traceable
            return ls_traceable(
                name=name or func.__name__,
                run_type=run_type,
                metadata=metadata or {},
            )(func)
        except ImportError:
            logger.warning("langsmith not installed, tracing disabled")
            return func

    return decorator


def wrap_openai_client(client):
    """
    Wrap an OpenAI client for automatic tracing.

    Args:
        client: OpenAI client instance

    Returns:
        Wrapped client with tracing enabled
    """
    if not LANGSMITH_ENABLED:
        return client

    try:
        from langsmith.wrappers import wrap_openai
        wrapped = wrap_openai(client)
        logger.debug("OpenAI client wrapped with LangSmith tracing")
        return wrapped
    except ImportError:
        logger.warning("langsmith not installed, returning unwrapped client")
        return client
    except Exception as e:
        logger.warning(f"Failed to wrap OpenAI client: {e}")
        return client


def wrap_anthropic_client(client):
    """
    Wrap an Anthropic client for automatic tracing.

    Note: As of Dec 2024, LangSmith's Anthropic wrapper may be experimental.
    Falls back to manual tracing if wrapper unavailable.

    Args:
        client: Anthropic client instance

    Returns:
        Wrapped client with tracing enabled (or original if wrapper unavailable)
    """
    if not LANGSMITH_ENABLED:
        return client

    try:
        # Try the wrapper if available
        from langsmith.wrappers import wrap_anthropic
        wrapped = wrap_anthropic(client)
        logger.debug("Anthropic client wrapped with LangSmith tracing")
        return wrapped
    except (ImportError, AttributeError):
        # Wrapper not available yet, return original
        # Manual tracing will be handled via @traceable on provider methods
        logger.debug("Anthropic wrapper not available, using manual tracing")
        return client
    except Exception as e:
        logger.warning(f"Failed to wrap Anthropic client: {e}")
        return client


def log_llm_call(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
    cost_usd: float,
    success: bool = True,
    error: Optional[str] = None,
):
    """
    Log an LLM call to LangSmith as a custom event.

    Use this for providers without automatic wrappers.
    """
    if not LANGSMITH_ENABLED:
        return

    try:
        client = get_langsmith_client()
        if client:
            # This could be extended to create custom runs
            # For now, just log to ensure data flows
            logger.debug(
                f"LLM call: {provider}/{model} "
                f"tokens={input_tokens}+{output_tokens} "
                f"latency={latency_ms}ms cost=${cost_usd:.4f}"
            )
    except Exception as e:
        logger.warning(f"Failed to log LLM call to LangSmith: {e}")


# Export public API
__all__ = [
    "LANGSMITH_ENABLED",
    "LANGSMITH_PROJECT",
    "get_langsmith_client",
    "traceable",
    "wrap_openai_client",
    "wrap_anthropic_client",
    "log_llm_call",
]
