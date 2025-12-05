"""
Authentication routes.

Uses FastAPI-Users for core authentication with custom invite code registration.

Endpoints:
    POST /auth/register     - Register with invite code (custom)
    POST /auth/jwt/login    - Login and get JWT token (FastAPI-Users)
    POST /auth/jwt/logout   - Logout (FastAPI-Users)
    GET  /auth/me           - Get current user info
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from src.auth.schemas import UserCreate, UserRead, UserUpdate
from src.auth.users import (
    auth_backend,
    current_active_user,
    fastapi_users,
    get_user_manager,
    UserManager,
)
from src.database import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()


# Custom registration endpoint with invite code validation
class RegisterRequest(UserCreate):
    """Registration request with invite code."""
    pass


class RegisterResponse(BaseModel):
    """Registration response."""
    id: str
    email: str
    role: str
    is_active: bool
    is_superuser: bool
    is_verified: bool


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    name="register:register",
)
async def register(
    request: Request,
    user_create: RegisterRequest,
    user_manager: UserManager = Depends(get_user_manager),
):
    """
    Register a new user with an invite code.

    The first user to register becomes a superuser/admin automatically.
    Subsequent users require a valid invite code.
    """
    # Check if this is the first user
    is_first_user = await user_manager.is_first_user()

    if is_first_user:
        # First user becomes superuser/admin
        user_create.is_superuser = True
        user_create.role = UserRole.ADMIN
        invite = None
    else:
        # Validate invite code
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
        # Create user using FastAPI-Users
        created_user = await user_manager.create(
            user_create,
            safe=True,  # Ignores is_superuser, is_verified from request unless we set them
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

    # Mark invite as used
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


# Include FastAPI-Users routes
router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/jwt",
    tags=["auth"],
)


# Current user endpoint
@router.get("/me", response_model=UserRead, tags=["auth"])
async def get_current_user_info(
    user: Annotated[User, Depends(current_active_user)],
):
    """Get the current authenticated user's info."""
    return user


# User management routes (for admins or self-management)
router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)
