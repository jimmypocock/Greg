"""
Admin service.

Handles admin operations for users and invites.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.exceptions import (
    CannotDeleteSelfError,
    CannotDemoteSelfError,
    CannotDisableSelfError,
    InvalidRoleError,
    InviteAlreadyUsedError,
    InviteGenerationError,
    InviteNotFoundError,
    UserNotFoundError,
)
from src.auth import generate_invite_code
from src.database import Invite, User, UserRole

if TYPE_CHECKING:
    from src.admin.schemas import InviteCreateRequest, UserUpdateRequest

logger = logging.getLogger(__name__)


class AdminService:
    """
    Admin service for user and invite management.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # User operations

    async def list_users(
        self,
        skip: int = 0,
        limit: int = 50,
        is_active: bool | None = None,
        role: str | None = None,
    ) -> tuple[list[User], int]:
        """List users with optional filtering."""
        query = select(User)

        if role:
            query = query.where(User.role == UserRole(role))
        if is_active is not None:
            query = query.where(User.is_active == is_active)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)

        query = query.offset(skip).limit(limit).order_by(User.created_at.desc())
        result = await self.session.execute(query)
        users = list(result.scalars().all())

        return users, total or 0

    async def get_user(self, user_id: uuid.UUID) -> User:
        """Get a user by ID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundError(str(user_id))

        return user

    async def update_user(
        self,
        user_id: uuid.UUID,
        admin_id: uuid.UUID,
        request: "UserUpdateRequest",
    ) -> User:
        """Update a user's role or active status."""
        user = await self.get_user(user_id)

        if user.id == admin_id and request.role == "user":
            raise CannotDemoteSelfError()

        if request.role is not None:
            try:
                user.role = UserRole(request.role)
            except ValueError:
                raise InvalidRoleError(request.role)

        if request.is_active is not None:
            if user.id == admin_id and not request.is_active:
                raise CannotDisableSelfError()
            user.is_active = request.is_active

        await self.session.commit()

        return user

    async def delete_user(self, user_id: uuid.UUID, admin_id: uuid.UUID) -> str:
        """Delete a user. Returns the deleted user's email."""
        user = await self.get_user(user_id)

        if user.id == admin_id:
            raise CannotDeleteSelfError()

        email = user.email
        await self.session.delete(user)
        await self.session.commit()

        return email

    # Invite operations

    async def list_invites(
        self,
        skip: int = 0,
        limit: int = 50,
        active: bool | None = None,
        used: bool | None = None,
    ) -> tuple[list[Invite], int]:
        """List invites with optional filtering."""
        query = select(Invite)

        if used is not None:
            if used:
                query = query.where(Invite.used_by != None)
            else:
                query = query.where(Invite.used_by == None)

        if active is not None:
            query = query.where(Invite.is_active == active)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)

        query = query.offset(skip).limit(limit).order_by(Invite.created_at.desc())
        result = await self.session.execute(query)
        invites = list(result.scalars().all())

        return invites, total or 0

    async def create_invite(
        self,
        admin_id: uuid.UUID,
        request: "InviteCreateRequest",
    ) -> Invite:
        """Create a new invite code."""
        expires_at = None
        if request.expires_in_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)

        max_retries = 3
        for attempt in range(max_retries):
            code = generate_invite_code()
            invite = Invite(
                code=code,
                email=request.email.lower() if request.email else None,
                created_by=admin_id,
                expires_at=expires_at,
            )
            self.session.add(invite)

            try:
                await self.session.commit()
                await self.session.refresh(invite)
                return invite
            except IntegrityError:
                await self.session.rollback()
                if attempt == max_retries - 1:
                    raise InviteGenerationError()

        raise InviteGenerationError()

    async def delete_invite(self, code: str) -> None:
        """Revoke an invite code."""
        result = await self.session.execute(select(Invite).where(Invite.code == code))
        invite = result.scalar_one_or_none()

        if not invite:
            raise InviteNotFoundError(code)

        if invite.used_by:
            raise InviteAlreadyUsedError()

        invite.is_active = False
        await self.session.commit()


async def get_admin_service(session: AsyncSession) -> AdminService:
    """Factory function for admin service."""
    return AdminService(session=session)
