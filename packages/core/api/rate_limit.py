"""
Rate limiting configuration.

Separated to avoid circular imports between app and routes.

Rate limits are applied per-user for authenticated requests,
falling back to per-IP for unauthenticated requests.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request


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


# Initialize rate limiter with user-aware key function
limiter = Limiter(key_func=get_rate_limit_key)


def get_limiter() -> Limiter:
    """Get the rate limiter instance for use in routes."""
    return limiter
