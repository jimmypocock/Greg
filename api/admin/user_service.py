"""
User admin service.

Handles admin operations for user management.
"""

import logging
import uuid
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.admin.exceptions import (
    CannotDeleteSelfError,
    CannotDemoteSelfError,
    CannotDisableSelfError,
    InvalidRoleError,
    UserNotFoundError,
)
from api.database import User, UserRole

if TYPE_CHECKING:
    from api.admin.schemas import UserUpdateRequest

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
        """
        List users with optional filtering.

        Args:
            skip: Number of records to skip for pagination.
            limit: Maximum number of records to return.
            is_active: Filter by active status.
            role: Filter by role name.

        Returns:
            Tuple of (users, total_count).
        """
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
        """
        Get a user by ID.

        Args:
            user_id: The user's UUID.

        Returns:
            The User object.

        Raises:
            UserNotFoundError: If user doesn't exist.
        """
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
        """
        Update a user's role or active status.

        Args:
            user_id: ID of the user to update.
            admin_id: ID of the admin performing the update.
            request: Update request with optional role and is_active.

        Returns:
            The updated User.

        Raises:
            UserNotFoundError: If user doesn't exist.
            CannotDemoteSelfError: If admin tries to remove their own admin role.
            CannotDisableSelfError: If admin tries to disable themselves.
            InvalidRoleError: If the specified role is invalid.
        """
        user = await self.get(user_id)
        changes = []

        if request.role is not None:
            try:
                new_role = UserRole(request.role)
            except ValueError:
                raise InvalidRoleError(request.role)

            # Prevent admin from removing their own admin privileges
            if user.id == admin_id and user.role == UserRole.ADMIN and new_role != UserRole.ADMIN:
                raise CannotDemoteSelfError()

            if user.role != new_role:
                old_role = user.role.value
                user.role = new_role
                changes.append(f"role {old_role} -> {new_role.value}")

        if request.is_active is not None:
            if user.id == admin_id and not request.is_active:
                raise CannotDisableSelfError()

            if user.is_active != request.is_active:
                user.is_active = request.is_active
                status = "activated" if request.is_active else "deactivated"
                changes.append(status)

        if changes:
            await self.session.commit()
            logger.info(f"User {user.email} updated by admin {admin_id}: {', '.join(changes)}")

        return user

    async def delete(self, user_id: uuid.UUID, admin_id: uuid.UUID) -> str:
        """
        Delete a user.

        Args:
            user_id: ID of the user to delete.
            admin_id: ID of the admin performing the deletion.

        Returns:
            The deleted user's email address.

        Raises:
            UserNotFoundError: If user doesn't exist.
            CannotDeleteSelfError: If admin tries to delete themselves.
        """
        user = await self.get(user_id)

        if user.id == admin_id:
            raise CannotDeleteSelfError()

        email = user.email
        await self.session.delete(user)
        await self.session.commit()

        logger.warning(f"User {email} deleted by admin {admin_id}")

        return email
