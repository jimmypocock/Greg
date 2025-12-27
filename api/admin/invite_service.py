"""
Invite admin service.

Handles admin operations for invite management.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.admin.exceptions import (
    InviteAlreadyUsedError,
    InviteGenerationError,
    InviteNotFoundError,
)
from api.auth import generate_invite_code
from api.database import Invite

if TYPE_CHECKING:
    from api.admin.schemas import InviteCreateRequest

logger = logging.getLogger(__name__)


class InviteService:
    """Service for admin invite operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list(
        self,
        skip: int = 0,
        limit: int = 50,
        active: bool | None = None,
        used: bool | None = None,
    ) -> tuple[list[Invite], int]:
        """
        List invites with optional filtering.

        Args:
            skip: Number of records to skip for pagination.
            limit: Maximum number of records to return.
            active: Filter by active status.
            used: Filter by used status.

        Returns:
            Tuple of (invites, total_count).
        """
        query = select(Invite)

        if used is not None:
            # Note: SQLAlchemy requires == None / != None (not `is None`)
            # to generate proper IS NULL / IS NOT NULL SQL
            if used:
                query = query.where(Invite.used_by != None)  # noqa: E711
            else:
                query = query.where(Invite.used_by == None)  # noqa: E711

        if active is not None:
            query = query.where(Invite.is_active == active)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.session.scalar(count_query)

        query = query.offset(skip).limit(limit).order_by(Invite.created_at.desc())
        result = await self.session.execute(query)
        invites = list(result.scalars().all())

        return invites, total or 0

    async def create(
        self,
        admin_id: uuid.UUID,
        request: "InviteCreateRequest",
    ) -> Invite:
        """
        Create a new invite code.

        Args:
            admin_id: ID of the admin creating the invite.
            request: Invite creation request with optional email and expiry.

        Returns:
            The created Invite.

        Raises:
            InviteGenerationError: If unique code generation fails.
        """
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

                target = f" for {request.email}" if request.email else ""
                logger.info(f"Invite {code} created by admin {admin_id}{target}")

                return invite
            except IntegrityError:
                await self.session.rollback()
                if attempt == max_retries - 1:
                    logger.error(f"Failed to generate unique invite code after {max_retries} attempts")
                    raise InviteGenerationError()

        raise InviteGenerationError()

    async def revoke(self, code: str, admin_id: uuid.UUID) -> None:
        """
        Revoke an invite code (soft delete).

        The invite is deactivated rather than deleted to preserve audit history.

        Args:
            code: The invite code to revoke.
            admin_id: ID of the admin revoking the invite.

        Raises:
            InviteNotFoundError: If the invite doesn't exist.
            InviteAlreadyUsedError: If the invite has already been used.
        """
        result = await self.session.execute(select(Invite).where(Invite.code == code))
        invite = result.scalar_one_or_none()

        if not invite:
            raise InviteNotFoundError(code)

        if invite.used_by:
            raise InviteAlreadyUsedError()

        invite.is_active = False
        await self.session.commit()

        logger.info(f"Invite {code} revoked by admin {admin_id}")
