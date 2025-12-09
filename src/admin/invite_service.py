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

from src.admin.exceptions import (
    InviteAlreadyUsedError,
    InviteGenerationError,
    InviteNotFoundError,
)
from src.auth import generate_invite_code
from src.database import Invite

if TYPE_CHECKING:
    from src.admin.schemas import InviteCreateRequest

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

    async def create(
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

    async def delete(self, code: str) -> None:
        """Revoke an invite code."""
        result = await self.session.execute(select(Invite).where(Invite.code == code))
        invite = result.scalar_one_or_none()

        if not invite:
            raise InviteNotFoundError(code)

        if invite.used_by:
            raise InviteAlreadyUsedError()

        invite.is_active = False
        await self.session.commit()
