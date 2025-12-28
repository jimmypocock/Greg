"""Store for managing song collaborators and share links."""

import logging
import secrets
from typing import Optional
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.enums import CollaboratorRole
from api.database.models import SongCollaborator, SongShareLink
from api.utils import utc_now

logger = logging.getLogger(__name__)


def generate_share_token() -> str:
    """Generate a secure URL-safe token for share links."""
    return secrets.token_urlsafe(48)  # 64 characters when base64 encoded


class CollaboratorStore:
    """Store for managing song collaborators."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # Collaborator CRUD

    async def get(self, collaborator_id: UUID) -> Optional[SongCollaborator]:
        """Get a collaborator by ID."""
        result = await self.session.execute(
            select(SongCollaborator).where(SongCollaborator.id == collaborator_id)
        )
        return result.scalar_one_or_none()

    async def get_by_song_and_user(
        self, song_id: UUID, user_id: UUID
    ) -> Optional[SongCollaborator]:
        """Get a collaborator record for a specific song and user."""
        result = await self.session.execute(
            select(SongCollaborator)
            .where(SongCollaborator.song_id == song_id)
            .where(SongCollaborator.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_by_song(self, song_id: UUID) -> list[SongCollaborator]:
        """List all collaborators for a song."""
        result = await self.session.execute(
            select(SongCollaborator)
            .where(SongCollaborator.song_id == song_id)
            .order_by(SongCollaborator.invited_at)
        )
        return list(result.scalars().all())

    async def list_by_user(
        self,
        user_id: UUID,
        role_filter: Optional[CollaboratorRole] = None,
    ) -> list[SongCollaborator]:
        """List all collaborator records for a user."""
        query = select(SongCollaborator).where(SongCollaborator.user_id == user_id)

        if role_filter:
            query = query.where(SongCollaborator.role == role_filter)

        result = await self.session.execute(query.order_by(SongCollaborator.invited_at))
        return list(result.scalars().all())

    async def create(
        self,
        song_id: UUID,
        user_id: UUID,
        role: CollaboratorRole,
        invited_by: Optional[UUID] = None,
        accepted: bool = False,
    ) -> SongCollaborator:
        """Create a new collaborator record."""
        collaborator = SongCollaborator(
            song_id=song_id,
            user_id=user_id,
            role=role,
            invited_by=invited_by,
            accepted_at=utc_now() if accepted else None,
        )
        self.session.add(collaborator)
        await self.session.commit()
        await self.session.refresh(collaborator)
        logger.info(f"Created collaborator {user_id} for song {song_id} with role {role}")
        return collaborator

    async def update_role(
        self, collaborator_id: UUID, new_role: CollaboratorRole
    ) -> Optional[SongCollaborator]:
        """Update a collaborator's role."""
        collaborator = await self.get(collaborator_id)
        if collaborator is None:
            return None

        collaborator.role = new_role
        await self.session.commit()
        await self.session.refresh(collaborator)
        logger.info(f"Updated collaborator {collaborator_id} to role {new_role}")
        return collaborator

    async def accept(self, collaborator_id: UUID) -> Optional[SongCollaborator]:
        """Accept a collaboration invitation."""
        collaborator = await self.get(collaborator_id)
        if collaborator is None:
            return None

        collaborator.accepted_at = utc_now()
        await self.session.commit()
        await self.session.refresh(collaborator)
        logger.info(f"Collaborator {collaborator_id} accepted invitation")
        return collaborator

    async def delete(self, collaborator_id: UUID) -> bool:
        """Delete a collaborator record."""
        result = await self.session.execute(
            delete(SongCollaborator).where(SongCollaborator.id == collaborator_id)
        )
        await self.session.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Deleted collaborator {collaborator_id}")
        return deleted

    async def delete_by_song_and_user(self, song_id: UUID, user_id: UUID) -> bool:
        """Delete a collaborator by song and user."""
        result = await self.session.execute(
            delete(SongCollaborator)
            .where(SongCollaborator.song_id == song_id)
            .where(SongCollaborator.user_id == user_id)
        )
        await self.session.commit()
        return result.rowcount > 0


class ShareLinkStore:
    """Store for managing song share links."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, link_id: UUID) -> Optional[SongShareLink]:
        """Get a share link by ID."""
        result = await self.session.execute(
            select(SongShareLink).where(SongShareLink.id == link_id)
        )
        return result.scalar_one_or_none()

    async def get_by_token(self, token: str) -> Optional[SongShareLink]:
        """Get a share link by token."""
        result = await self.session.execute(
            select(SongShareLink).where(SongShareLink.token == token)
        )
        return result.scalar_one_or_none()

    async def list_by_song(
        self, song_id: UUID, include_inactive: bool = False
    ) -> list[SongShareLink]:
        """List all share links for a song."""
        query = select(SongShareLink).where(SongShareLink.song_id == song_id)

        if not include_inactive:
            query = query.where(SongShareLink.is_active == True)

        result = await self.session.execute(query.order_by(SongShareLink.created_at.desc()))
        return list(result.scalars().all())

    async def create(
        self,
        song_id: UUID,
        created_by: UUID,
        role: CollaboratorRole = CollaboratorRole.VIEWER,
        expires_at=None,
        max_uses: Optional[int] = None,
    ) -> SongShareLink:
        """Create a new share link."""
        link = SongShareLink(
            song_id=song_id,
            token=generate_share_token(),
            role=role,
            created_by=created_by,
            expires_at=expires_at,
            max_uses=max_uses,
        )
        self.session.add(link)
        await self.session.commit()
        await self.session.refresh(link)
        logger.info(f"Created share link for song {song_id} with role {role}")
        return link

    async def deactivate(self, link_id: UUID) -> Optional[SongShareLink]:
        """Deactivate a share link."""
        link = await self.get(link_id)
        if link is None:
            return None

        link.is_active = False
        await self.session.commit()
        await self.session.refresh(link)
        logger.info(f"Deactivated share link {link_id}")
        return link

    async def delete(self, link_id: UUID) -> bool:
        """Delete a share link."""
        result = await self.session.execute(
            delete(SongShareLink).where(SongShareLink.id == link_id)
        )
        await self.session.commit()
        deleted = result.rowcount > 0
        if deleted:
            logger.info(f"Deleted share link {link_id}")
        return deleted

    async def increment_use_count(self, link_id: UUID) -> Optional[SongShareLink]:
        """Increment the use count of a share link."""
        link = await self.get(link_id)
        if link is None:
            return None

        link.increment_use_count()
        await self.session.commit()
        await self.session.refresh(link)
        return link
