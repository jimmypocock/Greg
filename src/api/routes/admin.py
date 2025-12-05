"""
Admin routes.

Endpoints:
    GET    /admin/users              - List all users
    GET    /admin/users/{user_id}    - Get user details
    PATCH  /admin/users/{user_id}    - Update user
    DELETE /admin/users/{user_id}    - Delete user
    POST   /admin/invites            - Create invite
    GET    /admin/invites            - List all invites
    DELETE /admin/invites/{code}     - Revoke invite
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import AdminUser, generate_invite_code
from src.database import (
    get_session_dependency,
    Invite,
    User,
    UserRole,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin"])


# Request/Response schemas
class UserUpdateRequest(BaseModel):
    """User update request body."""

    role: Optional[str] = None
    is_active: Optional[bool] = None


class InviteCreateRequest(BaseModel):
    """Invite creation request body."""

    email: Optional[EmailStr] = None
    expires_in_days: Optional[int] = 7


class UserListResponse(BaseModel):
    """User list response."""

    users: list[dict]
    total: int


class InviteListResponse(BaseModel):
    """Invite list response."""

    invites: list[dict]
    total: int


class InviteResponse(BaseModel):
    """Single invite response."""

    code: str
    signup_url: str
    email: Optional[str]
    expires_at: Optional[str]


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


# User management routes
@router.get("/users", response_model=UserListResponse)
async def list_users(
    admin: AdminUser,
    session: AsyncSession = Depends(get_session_dependency),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
):
    """List all users with optional filtering."""
    query = select(User)

    if role:
        query = query.where(User.role == UserRole(role))
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query)

    # Get users
    query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
    result = await session.execute(query)
    users = result.scalars().all()

    return UserListResponse(
        users=[user.to_dict() for user in users],
        total=total or 0,
    )


@router.get("/users/{user_id}")
async def get_user(
    user_id: UUID,
    admin: AdminUser,
    session: AsyncSession = Depends(get_session_dependency),
):
    """Get user details."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return {"user": user.to_dict()}


@router.patch("/users/{user_id}")
async def update_user(
    user_id: UUID,
    request: UserUpdateRequest,
    admin: AdminUser,
    session: AsyncSession = Depends(get_session_dependency),
):
    """Update user role or active status."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent admin from demoting themselves
    if user.id == admin.id and request.role == "user":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote yourself",
        )

    # Update fields
    if request.role is not None:
        try:
            user.role = UserRole(request.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid role: {request.role}",
            )

    if request.is_active is not None:
        # Prevent admin from disabling themselves
        if user.id == admin.id and not request.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot disable yourself",
            )
        user.is_active = request.is_active

    await session.commit()
    logger.info(f"Admin {admin.email} updated user {user.email}")

    return {"user": user.to_dict()}


@router.delete("/users/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: UUID,
    admin: AdminUser,
    session: AsyncSession = Depends(get_session_dependency),
):
    """Delete a user."""
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent admin from deleting themselves
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    email = user.email
    await session.delete(user)
    await session.commit()

    logger.info(f"Admin {admin.email} deleted user {email}")

    return MessageResponse(message=f"User {email} deleted")


# Invite management routes
@router.post("/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    request: InviteCreateRequest,
    admin: AdminUser,
    session: AsyncSession = Depends(get_session_dependency),
):
    """Create a new invite code."""
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)

    # Retry on collision (extremely rare)
    max_retries = 3
    for attempt in range(max_retries):
        code = generate_invite_code()
        invite = Invite(
            code=code,
            email=request.email.lower() if request.email else None,
            created_by=admin.id,
            expires_at=expires_at,
        )
        session.add(invite)

        try:
            await session.commit()
            break
        except IntegrityError:
            await session.rollback()
            if attempt == max_retries - 1:
                logger.error("Failed to generate unique invite code after retries")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to generate unique invite code",
                )
            logger.warning(f"Invite code collision, retrying ({attempt + 1}/{max_retries})")

    logger.info(f"Admin {admin.email} created invite {code}")

    # Build signup URL (assuming standard path)
    signup_url = f"/auth/signup?invite={code}"

    return InviteResponse(
        code=code,
        signup_url=signup_url,
        email=request.email,
        expires_at=expires_at.isoformat() if expires_at else None,
    )


@router.get("/invites", response_model=InviteListResponse)
async def list_invites(
    admin: AdminUser,
    session: AsyncSession = Depends(get_session_dependency),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    used: Optional[bool] = None,
    active: Optional[bool] = None,
):
    """List all invites with optional filtering."""
    query = select(Invite)

    if used is not None:
        if used:
            query = query.where(Invite.used_by != None)
        else:
            query = query.where(Invite.used_by == None)

    if active is not None:
        query = query.where(Invite.is_active == active)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await session.scalar(count_query)

    # Get invites
    query = query.offset(skip).limit(limit).order_by(Invite.created_at.desc())
    result = await session.execute(query)
    invites = result.scalars().all()

    return InviteListResponse(
        invites=[invite.to_dict() for invite in invites],
        total=total or 0,
    )


@router.delete("/invites/{code}", response_model=MessageResponse)
async def revoke_invite(
    code: str,
    admin: AdminUser,
    session: AsyncSession = Depends(get_session_dependency),
):
    """Revoke an invite code."""
    result = await session.execute(select(Invite).where(Invite.code == code))
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invite not found",
        )

    if invite.used_by:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot revoke used invite",
        )

    invite.is_active = False
    await session.commit()

    logger.info(f"Admin {admin.email} revoked invite {code}")

    return MessageResponse(message=f"Invite {code} revoked")
