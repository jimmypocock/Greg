"""
Token/authentication routes.

Provides login, logout, and token refresh endpoints.

Endpoints:
    POST /auth/token       - Login and get access + refresh tokens
    POST /auth/refresh     - Get new access token using refresh token
    POST /auth/logout      - Logout (revoke refresh token)
    POST /auth/logout-all  - Logout all sessions
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import jwt
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.api.rate_limit import limiter
from api.auth.refresh_tokens import revoke_all_user_tokens, revoke_refresh_token
from api.auth.schemas import (
    AccessTokenResponse,
    LoginRequest,
    MessageResponse,
    RefreshTokenRequest,
    TokenResponse,
)
from api.auth.users import UserManager, get_user_manager, SECRET_KEY
from api.auth import CurrentUser
from api.database import get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter()

# 2FA temp token settings
TEMP_TOKEN_EXPIRE_MINUTES = 5


# Routes


@router.post("/token", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    login_request: LoginRequest,
    user_manager: Annotated[UserManager, Depends(get_user_manager)],
):
    """Login with JSON body and receive access + refresh tokens.

    If the user has 2FA enabled, returns requires_2fa=True with a temp_token.
    Use the temp_token with /auth/2fa/verify to complete login.
    """
    result = await user_manager.login(
        email=login_request.email,
        password=login_request.password,
        device_info=_get_device_info(request),
        request=request,
    )

    # Check if user has 2FA enabled
    if result.user.totp_enabled:
        # Create a short-lived temp token for 2FA verification
        temp_token = _create_temp_token(str(result.user.id))
        logger.info(f"2FA required for user: {result.user.email}")

        return TokenResponse(
            requires_2fa=True,
            temp_token=temp_token,
        )

    logger.info(f"User logged in: {result.user.email}")

    return TokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
    )


@router.post("/refresh", response_model=AccessTokenResponse)
@limiter.limit("30/minute")
async def refresh_tokens(
    request: Request,
    token_request: RefreshTokenRequest,
    user_manager: Annotated[UserManager, Depends(get_user_manager)],
):
    """
    Get a new access token using a refresh token.

    The refresh token is rotated (old one invalidated, new one returned).
    """
    result = await user_manager.refresh_tokens(
        refresh_token=token_request.refresh_token,
        device_info=_get_device_info(request),
    )

    logger.info(f"Tokens refreshed for user: {result.user.email}")

    return AccessTokenResponse(
        access_token=result.access_token,
        refresh_token=result.refresh_token,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Logout by revoking the refresh token.

    The access token will remain valid until it expires (short-lived).
    """
    success = await revoke_refresh_token(session, request.refresh_token)

    if not success:
        logger.warning("Logout attempted with invalid token")

    return MessageResponse(message="Logged out successfully")


@router.post("/logout-all", response_model=MessageResponse)
async def logout_all_sessions(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
    keep_current: bool = False,
    current_refresh_token: str | None = None,
):
    """
    Logout from all sessions (revoke all refresh tokens).

    Optionally keep the current session by providing the current refresh token.
    """
    except_token = current_refresh_token if keep_current else None
    count = await revoke_all_user_tokens(session, user.id, except_token=except_token)

    return MessageResponse(message=f"Logged out from {count} session(s)")


# Private functions


def _get_device_info(request: Request) -> dict[str, Any]:
    """Extract device info from request for session tracking."""
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }


def _create_temp_token(user_id: str) -> str:
    """Create a short-lived temp token for 2FA verification."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=TEMP_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "type": "2fa_temp",
        "exp": expire,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")
