"""
User admin service.

Handles admin operations for user management.
"""

import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.admin.exceptions import (
    CannotDeleteSelfError,
    CannotDemoteSelfError,
    CannotDisableSelfError,
    InvalidRoleError,
    UserNotFoundError,
)
from src.database import User, UserRole

if TYPE_CHECKING:
    from src.admin.schemas import UserUpdateRequest

logger = logging.getLogger(__name__)


class UserService:
    """Service for admin user operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(
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

    async def get(self, user_id: uuid.UUID) -> User:
        """Get a user by ID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundError(str(user_id))

        return user

    async def update(
        self,
        user_id: uuid.UUID,
        admin_id: uuid.UUID,
        request: "UserUpdateRequest",
    ) -> User:
        """Update a user's role or active status."""
        user = await self.get(user_id)

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

    async def delete(self, user_id: uuid.UUID, admin_id: uuid.UUID) -> str:
        """Delete a user. Returns the deleted user's email."""
        user = await self.get(user_id)

        if user.id == admin_id:
            raise CannotDeleteSelfError()

        email = user.email
        await self.session.delete(user)
        await self.session.commit()

        return email
