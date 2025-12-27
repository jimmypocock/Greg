"""
Collaboration routes for the Songwriter app.

Manage collaborators and share links for songs.

Endpoints:
    POST   /songs/{song_id}/collaborators          - Add collaborator by user ID
    GET    /songs/{song_id}/collaborators          - List collaborators
    PUT    /songs/{song_id}/collaborators/{id}     - Update role (owner only)
    DELETE /songs/{song_id}/collaborators/{id}     - Remove collaborator (owner only)

    POST   /songs/{song_id}/share-links            - Create share link
    GET    /songs/{song_id}/share-links            - List share links
    DELETE /songs/{song_id}/share-links/{id}       - Revoke/delete share link

    POST   /share/{token}/accept                   - Accept share link (add self as collaborator)
    GET    /share/{token}                          - Get share link info (validates token)
"""

import logging
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import PermissionService
from api.enums import CollaboratorRole
from api.models import SongCollaborator, SongShareLink
from api.services.collaborator_store import CollaboratorStore, ShareLinkStore
from api.services.db_store import SongDBStore
from api.services.permissions import Permission
from api.auth import CurrentUser
from api.database import get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Collaboration"])


# Dependencies

async def get_collaborator_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> CollaboratorStore:
    """Get a collaborator store instance."""
    return CollaboratorStore(session)


async def get_share_link_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> ShareLinkStore:
    """Get a share link store instance."""
    return ShareLinkStore(session)


async def get_song_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> SongDBStore:
    """Get a song store instance."""
    return SongDBStore(session)


# Request/Response models

class AddCollaboratorRequest(BaseModel):
    """Request to add a collaborator."""

    user_id: UUID = Field(..., description="ID of the user to add as collaborator")
    role: CollaboratorRole = Field(
        CollaboratorRole.VIEWER,
        description="Role to assign (cannot assign OWNER)",
    )


class UpdateCollaboratorRequest(BaseModel):
    """Request to update a collaborator's role."""

    role: CollaboratorRole = Field(..., description="New role (cannot assign OWNER)")


class CollaboratorResponse(BaseModel):
    """Response for a collaborator."""

    id: UUID
    song_id: UUID
    user_id: UUID
    role: CollaboratorRole
    invited_by: Optional[UUID]
    invited_at: datetime
    accepted_at: Optional[datetime]
    is_pending: bool

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, collaborator: SongCollaborator) -> "CollaboratorResponse":
        """Create response from model."""
        return cls(
            id=collaborator.id,
            song_id=collaborator.song_id,
            user_id=collaborator.user_id,
            role=collaborator.role,
            invited_by=collaborator.invited_by,
            invited_at=collaborator.invited_at,
            accepted_at=collaborator.accepted_at,
            is_pending=collaborator.is_pending,
        )


class CollaboratorListResponse(BaseModel):
    """Response for listing collaborators."""

    collaborators: list[CollaboratorResponse]
    total: int


class CreateShareLinkRequest(BaseModel):
    """Request to create a share link."""

    role: CollaboratorRole = Field(
        CollaboratorRole.VIEWER,
        description="Role this link grants (cannot be OWNER)",
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="When the link expires (null = never)",
    )
    max_uses: Optional[int] = Field(
        None,
        ge=1,
        description="Maximum uses (null = unlimited)",
    )


class ShareLinkResponse(BaseModel):
    """Response for a share link."""

    id: UUID
    song_id: UUID
    token: str
    role: CollaboratorRole
    created_by: UUID
    created_at: datetime
    expires_at: Optional[datetime]
    max_uses: Optional[int]
    use_count: int
    is_active: bool
    is_valid: bool
    share_url: str = Field(..., description="Full URL to share")

    model_config = {"from_attributes": True}

    @classmethod
    def from_model(cls, link: SongShareLink, base_url: str = "") -> "ShareLinkResponse":
        """Create response from model."""
        return cls(
            id=link.id,
            song_id=link.song_id,
            token=link.token,
            role=link.role,
            created_by=link.created_by,
            created_at=link.created_at,
            expires_at=link.expires_at,
            max_uses=link.max_uses,
            use_count=link.use_count,
            is_active=link.is_active,
            is_valid=link.is_valid,
            share_url=f"{base_url}/share/{link.token}",
        )


class ShareLinkListResponse(BaseModel):
    """Response for listing share links."""

    share_links: list[ShareLinkResponse]
    total: int


class ShareLinkInfoResponse(BaseModel):
    """Public info about a share link (before accepting)."""

    song_id: UUID
    song_title: str
    role: CollaboratorRole
    is_valid: bool
    message: str


class AcceptShareLinkResponse(BaseModel):
    """Response after accepting a share link."""

    song_id: UUID
    song_title: str
    role: CollaboratorRole
    message: str


# Collaborator routes

@router.post(
    "/songs/{song_id}/collaborators",
    response_model=CollaboratorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_collaborator(
    song_id: UUID,
    request: AddCollaboratorRequest,
    user: CurrentUser,
    permission_service: PermissionService,
    collab_store: Annotated[CollaboratorStore, Depends(get_collaborator_store)],
):
    """Add a collaborator to a song.

    Only the owner can add collaborators directly.
    Cannot add yourself or assign OWNER role.
    """
    # Only owner can add collaborators
    await permission_service.require_permission(song_id, user.id, Permission.ADMIN)

    # Cannot add yourself
    if request.user_id == user.id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot add yourself as a collaborator",
        )

    # Cannot assign OWNER role
    if request.role == CollaboratorRole.OWNER:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot assign OWNER role. Transfer ownership through a different process.",
        )

    # Check if user already has access
    existing = await collab_store.get_by_song_and_user(song_id, request.user_id)
    if existing:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "User already has access to this song",
        )

    collaborator = await collab_store.create(
        song_id=song_id,
        user_id=request.user_id,
        role=request.role,
        invited_by=user.id,
        accepted=True,  # Direct invites are auto-accepted
    )

    logger.info(f"User {user.id} added collaborator {request.user_id} to song {song_id}")
    return CollaboratorResponse.from_model(collaborator)


@router.get("/songs/{song_id}/collaborators", response_model=CollaboratorListResponse)
async def list_collaborators(
    song_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    collab_store: Annotated[CollaboratorStore, Depends(get_collaborator_store)],
):
    """List all collaborators for a song.

    Any collaborator can view the list.
    """
    await permission_service.require_permission(song_id, user.id, Permission.READ)

    collaborators = await collab_store.list_by_song(song_id)

    return CollaboratorListResponse(
        collaborators=[CollaboratorResponse.from_model(c) for c in collaborators],
        total=len(collaborators),
    )


@router.put(
    "/songs/{song_id}/collaborators/{collaborator_id}",
    response_model=CollaboratorResponse,
)
async def update_collaborator(
    song_id: UUID,
    collaborator_id: UUID,
    request: UpdateCollaboratorRequest,
    user: CurrentUser,
    permission_service: PermissionService,
    collab_store: Annotated[CollaboratorStore, Depends(get_collaborator_store)],
):
    """Update a collaborator's role.

    Only the owner can change roles.
    Cannot change owner's role or assign OWNER role.
    """
    await permission_service.require_permission(song_id, user.id, Permission.ADMIN)

    collaborator = await collab_store.get(collaborator_id)
    if collaborator is None or collaborator.song_id != song_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collaborator not found")

    # Cannot change owner's role
    if collaborator.role == CollaboratorRole.OWNER:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot change owner's role",
        )

    # Cannot assign OWNER role
    if request.role == CollaboratorRole.OWNER:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot assign OWNER role",
        )

    updated = await collab_store.update_role(collaborator_id, request.role)
    logger.info(f"User {user.id} updated collaborator {collaborator_id} role to {request.role}")
    return CollaboratorResponse.from_model(updated)


@router.delete(
    "/songs/{song_id}/collaborators/{collaborator_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_collaborator(
    song_id: UUID,
    collaborator_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    collab_store: Annotated[CollaboratorStore, Depends(get_collaborator_store)],
):
    """Remove a collaborator from a song.

    Owner can remove any collaborator.
    Collaborators can remove themselves (leave the song).
    Cannot remove the owner.
    """
    collaborator = await collab_store.get(collaborator_id)
    if collaborator is None or collaborator.song_id != song_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Collaborator not found")

    # Cannot remove owner
    if collaborator.role == CollaboratorRole.OWNER:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot remove the owner",
        )

    # Check permission: either owner removing anyone, or user removing themselves
    is_owner = await permission_service.can_admin(song_id, user.id)
    is_self = collaborator.user_id == user.id

    if not (is_owner or is_self):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only the owner can remove other collaborators",
        )

    await collab_store.delete(collaborator_id)
    logger.info(f"User {user.id} removed collaborator {collaborator_id} from song {song_id}")


# Share link routes

@router.post(
    "/songs/{song_id}/share-links",
    response_model=ShareLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_share_link(
    song_id: UUID,
    request: CreateShareLinkRequest,
    user: CurrentUser,
    permission_service: PermissionService,
    link_store: Annotated[ShareLinkStore, Depends(get_share_link_store)],
):
    """Create a share link for a song.

    Only the owner can create share links.
    Cannot create links that grant OWNER role.
    """
    await permission_service.require_permission(song_id, user.id, Permission.ADMIN)

    if request.role == CollaboratorRole.OWNER:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot create share links that grant OWNER role",
        )

    link = await link_store.create(
        song_id=song_id,
        created_by=user.id,
        role=request.role,
        expires_at=request.expires_at,
        max_uses=request.max_uses,
    )

    logger.info(f"User {user.id} created share link for song {song_id}")
    return ShareLinkResponse.from_model(link)


@router.get("/songs/{song_id}/share-links", response_model=ShareLinkListResponse)
async def list_share_links(
    song_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    link_store: Annotated[ShareLinkStore, Depends(get_share_link_store)],
    include_inactive: bool = False,
):
    """List all share links for a song.

    Only the owner can view share links.
    """
    await permission_service.require_permission(song_id, user.id, Permission.ADMIN)

    links = await link_store.list_by_song(song_id, include_inactive=include_inactive)

    return ShareLinkListResponse(
        share_links=[ShareLinkResponse.from_model(link) for link in links],
        total=len(links),
    )


@router.delete(
    "/songs/{song_id}/share-links/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_share_link(
    song_id: UUID,
    link_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    link_store: Annotated[ShareLinkStore, Depends(get_share_link_store)],
):
    """Delete/revoke a share link.

    Only the owner can delete share links.
    """
    await permission_service.require_permission(song_id, user.id, Permission.ADMIN)

    link = await link_store.get(link_id)
    if link is None or link.song_id != song_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Share link not found")

    await link_store.delete(link_id)
    logger.info(f"User {user.id} deleted share link {link_id}")


# Public share link routes

@router.get("/share/{token}", response_model=ShareLinkInfoResponse)
async def get_share_link_info(
    token: str,
    user: CurrentUser,
    link_store: Annotated[ShareLinkStore, Depends(get_share_link_store)],
    song_store: Annotated[SongDBStore, Depends(get_song_store)],
):
    """Get information about a share link.

    Used to show the user what they're accepting before joining.
    Requires authentication to prevent enumeration attacks.
    """
    link = await link_store.get_by_token(token)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Share link not found")

    song = await song_store.get(link.song_id)
    if song is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    if not link.is_valid:
        return ShareLinkInfoResponse(
            song_id=link.song_id,
            song_title=song.title,
            role=link.role,
            is_valid=False,
            message="This share link has expired or reached its usage limit",
        )

    return ShareLinkInfoResponse(
        song_id=link.song_id,
        song_title=song.title,
        role=link.role,
        is_valid=True,
        message=f"You can join as {link.role.value}",
    )


@router.post("/share/{token}/accept", response_model=AcceptShareLinkResponse)
async def accept_share_link(
    token: str,
    user: CurrentUser,
    permission_service: PermissionService,
    link_store: Annotated[ShareLinkStore, Depends(get_share_link_store)],
    collab_store: Annotated[CollaboratorStore, Depends(get_collaborator_store)],
    song_store: Annotated[SongDBStore, Depends(get_song_store)],
):
    """Accept a share link and join as a collaborator.

    If user already has access, returns their existing access.
    """
    link = await link_store.get_by_token(token)
    if link is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Share link not found")

    song = await song_store.get(link.song_id)
    if song is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    if not link.is_valid:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "This share link has expired or reached its usage limit",
        )

    # Check if user already has access
    existing_role = await permission_service.get_user_role(link.song_id, user.id)
    if existing_role is not None:
        return AcceptShareLinkResponse(
            song_id=link.song_id,
            song_title=song.title,
            role=existing_role,
            message=f"You already have {existing_role.value} access to this song",
        )

    # Add user as collaborator
    await collab_store.create(
        song_id=link.song_id,
        user_id=user.id,
        role=link.role,
        invited_by=link.created_by,
        accepted=True,
    )

    # Increment link usage
    await link_store.increment_use_count(link.id)

    logger.info(f"User {user.id} joined song {link.song_id} via share link with role {link.role}")

    return AcceptShareLinkResponse(
        song_id=link.song_id,
        song_title=song.title,
        role=link.role,
        message=f"Successfully joined as {link.role.value}",
    )
