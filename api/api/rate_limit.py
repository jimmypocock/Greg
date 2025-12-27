"""
Rate limiting configuration.

Separated to avoid circular imports between app and routes.

Rate limits are applied per-user for authenticated requests,
falling back to per-IP for unauthenticated requests.

Default limits:
    - 200 requests/minute for authenticated users
    - 60 requests/minute for unauthenticated (IP-based)

Stricter limits are applied to sensitive endpoints like auth.
"""

import os

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

# Default rate limits (can be overridden via environment)
DEFAULT_RATE_LIMIT = os.getenv("RATE_LIMIT_DEFAULT", "200/minute")
UNAUTHENTICATED_RATE_LIMIT = os.getenv("RATE_LIMIT_UNAUTHENTICATED", "60/minute")


def get_rate_limit_key(request: Request) -> str:
    """
    Get the rate limit key for a request.

    - For authenticated users: uses user ID (from JWT)
    - For unauthenticated: uses IP address

    This ensures each user has their own rate limit bucket,
    preventing one user from consuming another's quota.
    """
    # Try to get user from request state (set by auth middleware)
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"

    # Fall back to IP address for unauthenticated requests
    return f"ip:{get_remote_address(request)}"


def get_dynamic_limit(key: str) -> str:
    """
    Return different rate limits based on whether user is authenticated.

    Authenticated users get a higher limit since we can track them reliably.
    Unauthenticated requests get a lower limit to prevent abuse.
    """
    if key.startswith("user:"):
        return DEFAULT_RATE_LIMIT
    return UNAUTHENTICATED_RATE_LIMIT


# Initialize rate limiter with user-aware key function and default limits
limiter = Limiter(
    key_func=get_rate_limit_key,
    default_limits=[get_dynamic_limit],
)


def get_limiter() -> Limiter:
    """Get the rate limiter instance for use in routes."""
    return limiter
