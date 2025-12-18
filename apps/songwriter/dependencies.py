"""FastAPI dependencies for the songwriter app."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Path
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.auth import CurrentUser
from packages.core.database import get_session_dependency

from apps.songwriter.services.permissions import Permission, SongPermissionService


# Dependency to get the permission service
async def get_permission_service(
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
) -> SongPermissionService:
    """Get a song permission service instance."""
    return SongPermissionService(session)


# Type alias for cleaner signatures
PermissionService = Annotated[SongPermissionService, Depends(get_permission_service)]


async def require_song_read(
    song_id: Annotated[UUID, Path()],
    user: CurrentUser,
    permission_service: PermissionService,
) -> UUID:
    """Dependency that requires read permission for a song.

    Returns the song_id if permission is granted.
    Raises HTTPException if user cannot access the song.
    """
    await permission_service.require_permission(song_id, user.id, Permission.READ)
    return song_id


async def require_song_write(
    song_id: Annotated[UUID, Path()],
    user: CurrentUser,
    permission_service: PermissionService,
) -> UUID:
    """Dependency that requires write permission for a song.

    Returns the song_id if permission is granted.
    Raises HTTPException if user cannot edit the song.
    """
    await permission_service.require_permission(song_id, user.id, Permission.WRITE)
    return song_id


async def require_song_admin(
    song_id: Annotated[UUID, Path()],
    user: CurrentUser,
    permission_service: PermissionService,
) -> UUID:
    """Dependency that requires admin permission for a song.

    Returns the song_id if permission is granted.
    Raises HTTPException if user is not the owner.
    """
    await permission_service.require_permission(song_id, user.id, Permission.ADMIN)
    return song_id


# Type aliases for route signatures
SongReadAccess = Annotated[UUID, Depends(require_song_read)]
SongWriteAccess = Annotated[UUID, Depends(require_song_write)]
SongAdminAccess = Annotated[UUID, Depends(require_song_admin)]
