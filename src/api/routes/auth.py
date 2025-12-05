"""
Authentication routes.

Provides JWT authentication with database-backed refresh tokens.

Endpoints:
    POST   /auth/register        - Register with invite code
    POST   /auth/login           - Login and get access + refresh tokens
    POST   /auth/refresh         - Get new access token using refresh token
    POST   /auth/logout          - Logout (revoke refresh token)
    POST   /auth/logout-all      - Logout all sessions
    GET    /auth/me              - Get current user info
    GET    /auth/sessions        - List active sessions
    DELETE /auth/sessions/{id}   - Revoke specific session
"""

import logging
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.refresh_tokens import (
    create_refresh_token,
    get_active_refresh_tokens,
    revoke_all_user_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
    validate_refresh_token,
)
from src.auth.schemas import (
    AccessTokenResponse,
    MessageResponse,
    RefreshTokenRequest,
    RegisterResponse,
    SessionListResponse,
    SessionResponse,
    TokenResponse,
    UserCreate,
    UserRead,
    UserUpdate,
)
from src.auth.users import (
    UserManager,
    current_active_user,
    fastapi_users,
    get_jwt_strategy,
    get_user_manager,
)
from src.database import RefreshToken, User, UserRole, get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Auth"])


# Public functions

@router.get("/me", response_model=UserRead)
async def get_current_user_info(
    user: Annotated[User, Depends(current_active_user)],
):
    """Get the current authenticated user's info."""
    return user


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    user: Annotated[User, Depends(current_active_user)],
    session: AsyncSession = Depends(get_session_dependency),
):
    """List all active sessions for the current user."""
    sessions = await get_active_refresh_tokens(session, user.id)

    return SessionListResponse(
        sessions=[
            SessionResponse(
                id=str(s.id),
                created_at=s.created_at.isoformat(),
                expires_at=s.expires_at.isoformat(),
                device_info=s.device_info,
            )
            for s in sessions
        ],
        count=len(sessions),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_manager: UserManager = Depends(get_user_manager),
    session: AsyncSession = Depends(get_session_dependency),
):
    """
    Login and receive access + refresh tokens.

    Use form data: username (email) and password.
    """
    user = await user_manager.authenticate(credentials=form_data)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwt_strategy = get_jwt_strategy()
    access_token = await jwt_strategy.write_token(user)

    device_info = _get_device_info(request)
    refresh_token_plain, _ = await create_refresh_token(
        session, user, device_info=device_info
    )

    await user_manager.on_after_login(user, request)

    logger.info(f"User logged in: {user.email}")

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_plain,
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session_dependency),
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
    user: Annotated[User, Depends(current_active_user)],
    session: AsyncSession = Depends(get_session_dependency),
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


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh_tokens(
    request: Request,
    token_request: RefreshTokenRequest,
    session: AsyncSession = Depends(get_session_dependency),
):
    """
    Get a new access token using a refresh token.

    The refresh token is rotated (old one invalidated, new one returned).
    """
    refresh_token = await validate_refresh_token(session, token_request.refresh_token)

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await session.execute(
        select(User).where(User.id == refresh_token.user_id)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )

    jwt_strategy = get_jwt_strategy()
    access_token = await jwt_strategy.write_token(user)

    device_info = _get_device_info(request)
    new_refresh_token_plain, _ = await rotate_refresh_token(
        session, refresh_token, device_info=device_info
    )

    logger.info(f"Tokens refreshed for user: {user.email}")

    return AccessTokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token_plain,
    )


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: Request,
    user_create: UserCreate,
    user_manager: UserManager = Depends(get_user_manager),
):
    """
    Register a new user with an invite code.

    The first user to register becomes a superuser/admin automatically.
    Subsequent users require a valid invite code.
    """
    is_first_user = await user_manager.is_first_user()

    if is_first_user:
        user_create.is_superuser = True
        user_create.role = UserRole.ADMIN
        invite = None
    else:
        invite = await user_manager.validate_invite_code(
            user_create.invite_code,
            user_create.email,
        )
        if not invite:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired invite code",
            )

    try:
        created_user = await user_manager.create(
            user_create,
            safe=True,
            request=request,
        )
    except Exception as e:
        error_msg = str(e)
        if "UNIQUE constraint" in error_msg or "duplicate key" in error_msg.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    if invite:
        await user_manager.mark_invite_used(invite, created_user.id)
        await user_manager.session.commit()

    logger.info(f"User registered: {created_user.email} (admin={is_first_user})")

    return RegisterResponse(
        id=str(created_user.id),
        email=created_user.email,
        role=created_user.role.value,
        is_active=created_user.is_active,
        is_superuser=created_user.is_superuser,
        is_verified=created_user.is_verified,
    )


@router.delete("/sessions/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: str,
    user: Annotated[User, Depends(current_active_user)],
    session: AsyncSession = Depends(get_session_dependency),
):
    """Revoke a specific session by ID."""
    try:
        token_uuid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid session ID",
        )

    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.id == token_uuid,
            RefreshToken.user_id == user.id,
        )
    )
    refresh_token = result.scalar_one_or_none()

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    if refresh_token.is_revoked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already revoked",
        )

    refresh_token.revoke()
    await session.commit()

    logger.info(f"User {user.email} revoked session {session_id}")

    return MessageResponse(message="Session revoked")


# Include FastAPI-Users routes

router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["Users"],
)


# Private functions

def _get_device_info(request: Request) -> dict[str, Any]:
    """Extract device info from request for session tracking."""
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }
