"""
Authentication dependencies for FastAPI routes.

Provides dependency injection for user authentication and authorization.
Integrates with FastAPI-Users while supporting custom API key authentication.
"""

import hashlib
import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.users import current_active_user, optional_current_user
from src.database import APIKey, User, UserRole, get_session_dependency

logger = logging.getLogger(__name__)

# Security scheme for API key bearer tokens
api_key_scheme = HTTPBearer(auto_error=False)


def hash_token(token: str) -> str:
    """Hash a token for storage/comparison."""
    return hashlib.sha256(token.encode()).hexdigest()


async def _authenticate_api_key(key: str, session: AsyncSession) -> User:
    """Authenticate using API key."""
    key_hash = hash_token(key)

    result = await session.execute(
        select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True,
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )

    # Check if expired
    if api_key.expires_at and datetime.now(timezone.utc) > api_key.expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    # Update last used
    api_key.last_used_at = datetime.now(timezone.utc)

    # Get user
    result = await session.execute(select(User).where(User.id == api_key.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )

    return user


async def get_current_user_with_api_key(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(api_key_scheme)],
    jwt_user: Annotated[User | None, Depends(optional_current_user)],
    session: AsyncSession = Depends(get_session_dependency),
) -> User:
    """
    Get the current authenticated user from JWT token or API key.

    Checks for:
    1. JWT token (via FastAPI-Users)
    2. API key (if starts with "greg_")

    Raises:
        HTTPException: If not authenticated or token invalid.
    """
    # First check if JWT authentication succeeded
    if jwt_user is not None:
        return jwt_user

    # Then check for API key
    if credentials and credentials.credentials.startswith("greg_"):
        return await _authenticate_api_key(credentials.credentials, session)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user_optional_with_api_key(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(api_key_scheme)],
    jwt_user: Annotated[User | None, Depends(optional_current_user)],
    session: AsyncSession = Depends(get_session_dependency),
) -> User | None:
    """
    Get the current user if authenticated, None otherwise.

    Use this for routes that work both authenticated and unauthenticated.
    """
    if jwt_user is not None:
        return jwt_user

    if credentials and credentials.credentials.startswith("greg_"):
        try:
            return await _authenticate_api_key(credentials.credentials, session)
        except HTTPException:
            return None

    return None


def require_admin(user: User = Depends(get_current_user_with_api_key)) -> User:
    """
    Require admin role or superuser.

    Raises:
        HTTPException: If user is not admin.
    """
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


# Type aliases for cleaner dependency injection
CurrentUser = Annotated[User, Depends(get_current_user_with_api_key)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional_with_api_key)]
AdminUser = Annotated[User, Depends(require_admin)]

# Re-export FastAPI-Users dependencies for convenience
__all__ = [
    "get_current_user_with_api_key",
    "get_current_user_optional_with_api_key",
    "require_admin",
    "CurrentUser",
    "OptionalUser",
    "AdminUser",
    "hash_token",
]
