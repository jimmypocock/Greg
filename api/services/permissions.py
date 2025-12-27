"""Permission service for song access control."""

import logging
from enum import Enum
from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.enums import CollaboratorRole
from api.models import Song, SongCollaborator, SongShareLink

logger = logging.getLogger(__name__)


class Permission(str, Enum):
    """Permission levels for song access."""

    READ = "read"  # Can view the song
    WRITE = "write"  # Can edit the song (owner or editor)
    ADMIN = "admin"  # Can manage collaborators, delete song (owner only)


class SongPermissionService:
    """Service for checking and enforcing song permissions."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user_role(
        self,
        song_id: UUID,
        user_id: UUID,
    ) -> Optional[CollaboratorRole]:
        """Get user's role for a song.

        Returns None if user has no access.
        """
        # Check if user is the song owner
        song_result = await self.session.execute(
            select(Song.owner_id).where(Song.id == song_id)
        )
        owner_id = song_result.scalar_one_or_none()

        if owner_id is None:
            return None  # Song doesn't exist

        if owner_id == user_id:
            return CollaboratorRole.OWNER

        # Check collaborator record
        collab_result = await self.session.execute(
            select(SongCollaborator.role)
            .where(SongCollaborator.song_id == song_id)
            .where(SongCollaborator.user_id == user_id)
        )
        role = collab_result.scalar_one_or_none()

        return role

    async def can_read(self, song_id: UUID, user_id: UUID) -> bool:
        """Check if user can view the song."""
        role = await self.get_user_role(song_id, user_id)
        return role is not None

    async def can_write(self, song_id: UUID, user_id: UUID) -> bool:
        """Check if user can edit the song (owner or editor)."""
        role = await self.get_user_role(song_id, user_id)
        return role in (CollaboratorRole.OWNER, CollaboratorRole.EDITOR)

    async def can_admin(self, song_id: UUID, user_id: UUID) -> bool:
        """Check if user can manage the song (owner only)."""
        role = await self.get_user_role(song_id, user_id)
        return role == CollaboratorRole.OWNER

    async def require_permission(
        self,
        song_id: UUID,
        user_id: UUID,
        permission: Permission,
    ) -> CollaboratorRole:
        """Require a specific permission level.

        Args:
            song_id: The song to check access for
            user_id: The user requesting access
            permission: The required permission level

        Returns:
            The user's role if permission granted

        Raises:
            HTTPException: 404 if song not found or no access, 403 if insufficient permission
        """
        role = await self.get_user_role(song_id, user_id)

        if role is None:
            # Don't reveal whether song exists or user has no access
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Song not found: {song_id}",
            )

        if permission == Permission.READ:
            # Any role can read
            return role

        if permission == Permission.WRITE:
            if role not in (CollaboratorRole.OWNER, CollaboratorRole.EDITOR):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to edit this song",
                )
            return role

        if permission == Permission.ADMIN:
            if role != CollaboratorRole.OWNER:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Only the owner can perform this action",
                )
            return role

        return role

    async def get_accessible_songs(
        self,
        user_id: UUID,
        role_filter: Optional[CollaboratorRole] = None,
    ) -> list[UUID]:
        """Get list of song IDs the user can access.

        Args:
            user_id: The user to get accessible songs for
            role_filter: Optional filter for specific role

        Returns:
            List of song IDs the user can access
        """
        # Songs where user is owner
        owned_query = select(Song.id).where(Song.owner_id == user_id)

        # Songs where user is a collaborator
        collab_query = select(SongCollaborator.song_id).where(
            SongCollaborator.user_id == user_id
        )

        if role_filter:
            if role_filter == CollaboratorRole.OWNER:
                # Only owned songs
                result = await self.session.execute(owned_query)
            else:
                # Only collaborator with specific role
                collab_query = collab_query.where(SongCollaborator.role == role_filter)
                result = await self.session.execute(collab_query)
        else:
            # All accessible songs (owned + collaborated)
            result = await self.session.execute(
                select(Song.id).where(
                    or_(
                        Song.owner_id == user_id,
                        Song.id.in_(
                            select(SongCollaborator.song_id).where(
                                SongCollaborator.user_id == user_id
                            )
                        ),
                    )
                )
            )

        return list(result.scalars().all())

    async def validate_share_link(
        self,
        token: str,
    ) -> Optional[SongShareLink]:
        """Validate a share link and return it if valid.

        Returns None if:
        - Link doesn't exist
        - Link is inactive
        - Link is expired
        - Link has reached max uses
        """
        result = await self.session.execute(
            select(SongShareLink).where(SongShareLink.token == token)
        )
        link = result.scalar_one_or_none()

        if link is None:
            return None

        if not link.is_valid:
            return None

        return link

    async def use_share_link(
        self,
        token: str,
        user_id: UUID,
    ) -> Optional[SongCollaborator]:
        """Use a share link to add a user as a collaborator.

        Returns the created collaborator, or None if link is invalid
        or user already has access.
        """
        link = await self.validate_share_link(token)
        if link is None:
            return None

        # Check if user already has access
        existing_role = await self.get_user_role(link.song_id, user_id)
        if existing_role is not None:
            # User already has access, don't add again
            return None

        # Create collaborator record
        from api.models.utils import utc_now

        collaborator = SongCollaborator(
            song_id=link.song_id,
            user_id=user_id,
            role=link.role,
            invited_by=link.created_by,
            accepted_at=utc_now(),
        )

        self.session.add(collaborator)

        # Increment link usage
        link.increment_use_count()

        await self.session.commit()
        await self.session.refresh(collaborator)

        logger.info(
            f"User {user_id} joined song {link.song_id} via share link "
            f"with role {link.role.value}"
        )

        return collaborator
