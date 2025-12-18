"""
Internal API key validation for server-to-server communication.

This validates that requests come from trusted servers (like Next.js API routes)
rather than directly from browsers or untrusted clients.

Usage:
    For routes that should ONLY be called from your server (not browsers):

    @router.post("/ai/generate")
    async def generate(
        user: CurrentUser,
        _internal: Annotated[None, Depends(require_internal_api_key)],
    ):
        # This can only be called with valid internal API key
        ...

    For optional validation (allows direct calls in development):

    @router.post("/ai/generate")
    async def generate(
        user: CurrentUser,
        is_internal: Annotated[bool, Depends(check_internal_api_key)],
    ):
        if not is_internal and Config.INTERNAL_API_KEY:
            # In production with key configured, reject direct calls
            raise HTTPException(403, "Must be called from server")
        ...
"""

import logging
import secrets
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from packages.core.config import Config

logger = logging.getLogger(__name__)

# Header name for internal API key
INTERNAL_API_KEY_HEADER = "X-Internal-API-Key"


def check_internal_api_key(
    api_key: Optional[str] = Header(None, alias=INTERNAL_API_KEY_HEADER),
) -> bool:
    """
    Check if request has valid internal API key.

    Returns True if key is valid, False otherwise.
    Does NOT raise exception - use for optional checks.
    """
    configured_key = Config.INTERNAL_API_KEY

    # If no key configured, internal API is disabled
    if not configured_key:
        return False

    # If no key provided in request
    if not api_key:
        return False

    # Use constant-time comparison to prevent timing attacks
    return secrets.compare_digest(api_key, configured_key)


def require_internal_api_key(
    api_key: Optional[str] = Header(None, alias=INTERNAL_API_KEY_HEADER),
) -> None:
    """
    Require valid internal API key.

    Raises HTTPException 403 if:
    - Internal API key is configured but not provided
    - Internal API key is provided but doesn't match

    Does nothing if internal API key is not configured (development mode).
    """
    configured_key = Config.INTERNAL_API_KEY

    # If no key configured, allow all requests (development mode)
    if not configured_key:
        logger.debug("Internal API key not configured - allowing request")
        return

    # If key is configured, require it
    if not api_key:
        logger.warning("Internal API key required but not provided")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Internal API key required",
        )

    if not secrets.compare_digest(api_key, configured_key):
        logger.warning("Invalid internal API key provided")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid internal API key",
        )


class RequireInternalOrAdmin:
    """
    Dependency that requires either internal API key OR admin user.

    Useful for routes that can be called:
    - By the Next.js server (with internal key) on behalf of any user
    - Directly by admin users (for testing/admin tools)
    """

    async def __call__(
        self,
        api_key: Optional[str] = Header(None, alias=INTERNAL_API_KEY_HEADER),
    ) -> bool:
        """
        Returns True if internal key is valid, False if not (but may still proceed if admin).
        The route handler should check user.is_admin if this returns False.
        """
        return check_internal_api_key(api_key)
