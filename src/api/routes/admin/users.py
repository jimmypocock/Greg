"""
Admin user management routes.

Provides admin-only endpoints for user management.

Endpoints:
    GET    /admin/users              - List all users
    GET    /admin/users/{user_id}    - Get user details
    PATCH  /admin/users/{user_id}    - Update user
    DELETE /admin/users/{user_id}    - Delete user
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin import (
    MessageResponse,
    UserListResponse,
    UserResponse,
    UserService,
    UserUpdateRequest,
)
from src.auth import AdminUser
from src.database import get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependencies


async def get_user_service(
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
) -> UserService:
    """Get user service with session."""
    return UserService(session=session)


# Routes


@router.get("", response_model=UserListResponse)
async def list_users(
    admin: AdminUser,
    service: Annotated[UserService, Depends(get_user_service)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    is_active: bool | None = None,
    role: str | None = None,
):
    """List all users with optional filtering."""
    users, total = await service.list(skip, limit, is_active, role)

    return UserListResponse(
        users=[user.to_dict() for user in users],
        total=total,
    )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    admin: AdminUser,
    service: Annotated[UserService, Depends(get_user_service)],
):
    """Get user details."""
    user = await service.get(user_id)

    return UserResponse(user=user.to_dict())


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    admin: AdminUser,
    service: Annotated[UserService, Depends(get_user_service)],
):
    """Update user role or active status."""
    user = await service.update(user_id, admin.id, request)

    logger.info(f"Admin {admin.email} updated user {user.email}")

    return UserResponse(user=user.to_dict())


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: UUID,
    admin: AdminUser,
    service: Annotated[UserService, Depends(get_user_service)],
):
    """Delete a user."""
    email = await service.delete(user_id, admin.id)

    logger.info(f"Admin {admin.email} deleted user {email}")

    return MessageResponse(message=f"User {email} deleted")
