"""Core utilities."""

from datetime import datetime, timezone


def utc_now() -> datetime:
    """Get current UTC time (Python 3.12+ compatible).

    Use this instead of datetime.utcnow() which is deprecated.
    """
    return datetime.now(timezone.utc)
