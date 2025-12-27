"""
Authentication dependencies for FastAPI routes.

Provides dependency injection for user authentication and authorization.
Integrates with FastAPI-Users while supporting custom API key authentication.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth.tokens import hash_token
from api.auth.users import optional_current_user
from api.database import APIKey, User, get_session_dependency

logger = logging.getLogger(__name__)

api_key_scheme = HTTPBearer(auto_error=False)


# Classes

@dataclass
class AuthContext:
    """
    Authentication context containing user and optional API key info.

    Attributes:
        user: The authenticated user.
        api_key_id: The API key ID if authenticated via API key, None if JWT.
    """

    user: User
    api_key_id: uuid.UUID | None = None

    @property
    def is_api_key_auth(self) -> bool:
        """True if authenticated via API key."""
        return self.api_key_id is not None


# Public functions

async def get_auth_context(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(api_key_scheme)],
    jwt_user: Annotated[User | None, Depends(optional_current_user)],
    session: AsyncSession = Depends(get_session_dependency),
) -> AuthContext:
    """
    Get the authentication context with user and optional API key info.

    Checks for:
    1. JWT token (via FastAPI-Users)
    2. API key (if starts with "greg_")

    Raises:
        HTTPException: If not authenticated or token invalid.
    """
    if jwt_user is not None:
        return AuthContext(user=jwt_user, api_key_id=None)

    if credentials and credentials.credentials.startswith("greg_"):
        user, api_key_id = await _authenticate_api_key(credentials.credentials, session)
        return AuthContext(user=user, api_key_id=api_key_id)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_auth_context_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(api_key_scheme)],
    jwt_user: Annotated[User | None, Depends(optional_current_user)],
    session: AsyncSession = Depends(get_session_dependency),
) -> AuthContext | None:
    """
    Get the authentication context if authenticated, None otherwise.

    Use this for routes that work both authenticated and unauthenticated.
    """
    if jwt_user is not None:
        return AuthContext(user=jwt_user, api_key_id=None)

    if credentials and credentials.credentials.startswith("greg_"):
        try:
            user, api_key_id = await _authenticate_api_key(credentials.credentials, session)
            return AuthContext(user=user, api_key_id=api_key_id)
        except HTTPException:
            return None

    return None


async def get_current_user_with_api_key(
    auth: Annotated[AuthContext, Depends(get_auth_context)],
) -> User:
    """
    Get the current authenticated user from JWT token or API key.

    This is a convenience wrapper for routes that only need the user.
    """
    return auth.user


async def get_current_user_optional_with_api_key(
    auth: Annotated[AuthContext | None, Depends(get_auth_context_optional)],
) -> User | None:
    """
    Get the current user if authenticated, None otherwise.

    This is a convenience wrapper for routes that only need the user.
    """
    return auth.user if auth else None


def require_admin(auth: AuthContext = Depends(get_auth_context)) -> AuthContext:
    """
    Require admin role or superuser.

    Raises:
        HTTPException: If user is not admin.
    """
    if not auth.user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return auth


# Private functions

async def _authenticate_api_key(
    key: str,
    session: AsyncSession,
) -> tuple[User, uuid.UUID]:
    """
    Authenticate using API key.

    Returns:
        Tuple of (user, api_key_id).
    """
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

    if api_key.expires_at and datetime.now(timezone.utc) > api_key.expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key has expired",
        )

    api_key.last_used_at = datetime.now(timezone.utc)

    result = await session.execute(select(User).where(User.id == api_key.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
        )

    return user, api_key.id


# Type aliases

Auth = Annotated[AuthContext, Depends(get_auth_context)]
MaybeAuth = Annotated[AuthContext | None, Depends(get_auth_context_optional)]
AdminAuth = Annotated[AuthContext, Depends(require_admin)]

# User-only aliases (when you don't need full AuthContext)
CurrentUser = Annotated[User, Depends(get_current_user_with_api_key)]


async def _get_admin_user(auth: AuthContext = Depends(require_admin)) -> User:
    """Extract user from admin auth context."""
    return auth.user


AdminUser = Annotated[User, Depends(_get_admin_user)]


__all__ = [
    # Classes
    "AuthContext",
    # New type aliases (preferred)
    "AdminAuth",
    "Auth",
    "MaybeAuth",
    # User-only type aliases
    "AdminUser",
    "CurrentUser",
    # Functions
    "get_auth_context",
    "get_auth_context_optional",
    "get_current_user_optional_with_api_key",
    "get_current_user_with_api_key",
    "require_admin",
]
