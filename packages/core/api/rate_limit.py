"""
Rate limiting configuration.

Separated to avoid circular imports between app and routes.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)


def get_limiter() -> Limiter:
    """Get the rate limiter instance for use in routes."""
    return limiter
