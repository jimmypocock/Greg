"""
Section version routes for the Songwriter app.

Endpoints:
    GET    /songs/{song_id}/sections/{section_id}/versions              - List versions
    POST   /songs/{song_id}/sections/{section_id}/versions              - Create version
    GET    /songs/{song_id}/sections/{section_id}/versions/{id}         - Get version
    PUT    /songs/{song_id}/sections/{section_id}/versions/{id}         - Update version
    DELETE /songs/{song_id}/sections/{section_id}/versions/{id}         - Delete version
    POST   /songs/{song_id}/sections/{section_id}/versions/{id}/duplicate  - Duplicate
    POST   /songs/{song_id}/sections/{section_id}/versions/{id}/promote    - Promote to main
"""

import logging
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import PermissionService
from api.database.models import Line, SectionVersion
from api.services.db_store import SongDBStore
from api.services.permissions import Permission
from api.services.version_store import SectionVersionStore
from api.auth import CurrentUser
from api.database import get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/songs/{song_id}/sections/{section_id}/versions",
    tags=["Section Versions"],
)


# Dependencies

async def get_db_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> SongDBStore:
    """Get a database-backed song store."""
    return SongDBStore(session)


async def get_version_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> SectionVersionStore:
    """Get a database-backed version store."""
    return SectionVersionStore(session)


# Response models

class ChordResponse(BaseModel):
    """Chord placement response."""

    id: UUID
    chord: str
    position: int

    model_config = {"from_attributes": True}


class LineResponse(BaseModel):
    """Line response for API."""

    id: UUID
    text: str
    order: int
    notes: Optional[str]
    chords: list[ChordResponse]

    model_config = {"from_attributes": True}

    @classmethod
    def from_line(cls, line: Line) -> "LineResponse":
        """Convert a Line model to a response."""
        return cls(
            id=line.id,
            text=line.text,
            order=line.order,
            notes=line.notes,
            chords=[
                ChordResponse(id=c.id, chord=c.chord, position=c.position)
                for c in sorted(line.chords, key=lambda c: c.position)
            ],
        )


class SectionVersionResponse(BaseModel):
    """Full section version response."""

    id: UUID
    section_id: UUID
    version_number: int
    name: Optional[str]
    is_main: bool
    notes: Optional[str]
    lines: list[LineResponse]
    line_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_version(cls, version: SectionVersion) -> "SectionVersionResponse":
        """Convert a SectionVersion model to a response."""
        sorted_lines = sorted(version.lines, key=lambda l: l.order)
        return cls(
            id=version.id,
            section_id=version.section_id,
            version_number=version.version_number,
            name=version.name,
            is_main=version.is_main,
            notes=version.notes,
            lines=[LineResponse.from_line(line) for line in sorted_lines],
            line_count=len(version.lines),
            created_at=version.created_at,
            updated_at=version.updated_at,
        )


class SectionVersionSummary(BaseModel):
    """Summary of a section version for list views."""

    id: UUID
    version_number: int
    name: Optional[str]
    is_main: bool
    line_count: int
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_version(cls, version: SectionVersion) -> "SectionVersionSummary":
        """Convert a SectionVersion model to a summary."""
        return cls(
            id=version.id,
            version_number=version.version_number,
            name=version.name,
            is_main=version.is_main,
            line_count=len(version.lines) if version.lines else 0,
            created_at=version.created_at,
        )


class VersionListResponse(BaseModel):
    """Response for listing versions."""

    versions: list[SectionVersionSummary]
    total: int


# Request models

class CreateVersionRequest(BaseModel):
    """Request to create a new version."""

    name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    duplicate_from_version_id: Optional[UUID] = Field(
        None,
        description="If provided, copy lines from this version",
    )


class UpdateVersionRequest(BaseModel):
    """Request to update a version's metadata."""

    name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


# Helper to verify song and section exist

async def verify_song_and_section(
    song_id: UUID,
    section_id: UUID,
    user_id: UUID,
    permission: Permission,
    store: SongDBStore,
    permission_service: PermissionService,
) -> None:
    """Verify the song exists, user has permission, and contains the section."""
    # Check permission (raises 404 if song not found or no access, 403 if insufficient)
    await permission_service.require_permission(song_id, user_id, permission)

    song = await store.get(song_id)
    if song is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Song not found")

    section_ids = {s.id for s in song.sections}
    if section_id not in section_ids:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Section not found in song")


# Routes

@router.get("/", response_model=VersionListResponse)
async def list_versions(
    song_id: UUID,
    section_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    store: SongDBStore = Depends(get_db_store),
    version_store: SectionVersionStore = Depends(get_version_store),
):
    """List all versions for a section."""
    await verify_song_and_section(
        song_id, section_id, user.id, Permission.READ, store, permission_service
    )

    versions = await version_store.list_by_section(section_id)

    return VersionListResponse(
        versions=[SectionVersionSummary.from_version(v) for v in versions],
        total=len(versions),
    )


@router.post("/", response_model=SectionVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_version(
    song_id: UUID,
    section_id: UUID,
    request: CreateVersionRequest,
    user: CurrentUser,
    permission_service: PermissionService,
    store: SongDBStore = Depends(get_db_store),
    version_store: SectionVersionStore = Depends(get_version_store),
):
    """Create a new version for a section.

    If duplicate_from_version_id is provided, copies all lines from that version.
    """
    await verify_song_and_section(
        song_id, section_id, user.id, Permission.WRITE, store, permission_service
    )

    if request.duplicate_from_version_id:
        # Duplicate from existing version
        version = await version_store.duplicate(
            request.duplicate_from_version_id,
            name=request.name,
        )
        if version is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Source version not found")
    else:
        # Create empty version
        version = await version_store.create(
            section_id=section_id,
            name=request.name,
            is_main=False,
        )

    if request.notes:
        version = await version_store.update(version.id, {"notes": request.notes})

    logger.info(f"Created version {version.id} for section {section_id}")
    return SectionVersionResponse.from_version(version)


@router.get("/{version_id}", response_model=SectionVersionResponse)
async def get_version(
    song_id: UUID,
    section_id: UUID,
    version_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    store: SongDBStore = Depends(get_db_store),
    version_store: SectionVersionStore = Depends(get_version_store),
):
    """Get a specific version with all its lines."""
    await verify_song_and_section(
        song_id, section_id, user.id, Permission.READ, store, permission_service
    )

    version = await version_store.get(version_id)
    if version is None or version.section_id != section_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Version not found")

    return SectionVersionResponse.from_version(version)


@router.put("/{version_id}", response_model=SectionVersionResponse)
async def update_version(
    song_id: UUID,
    section_id: UUID,
    version_id: UUID,
    request: UpdateVersionRequest,
    user: CurrentUser,
    permission_service: PermissionService,
    store: SongDBStore = Depends(get_db_store),
    version_store: SectionVersionStore = Depends(get_version_store),
):
    """Update a version's metadata (name, notes)."""
    await verify_song_and_section(
        song_id, section_id, user.id, Permission.WRITE, store, permission_service
    )

    version = await version_store.get(version_id)
    if version is None or version.section_id != section_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Version not found")

    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.notes is not None:
        updates["notes"] = request.notes

    if updates:
        version = await version_store.update(version_id, updates)
        logger.info(f"Updated version {version_id}: {updates}")

    return SectionVersionResponse.from_version(version)


@router.delete("/{version_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_version(
    song_id: UUID,
    section_id: UUID,
    version_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    store: SongDBStore = Depends(get_db_store),
    version_store: SectionVersionStore = Depends(get_version_store),
):
    """Delete a version.

    Cannot delete the last remaining version of a section.
    If deleting the main version, another version will be promoted.
    """
    await verify_song_and_section(
        song_id, section_id, user.id, Permission.WRITE, store, permission_service
    )

    version = await version_store.get(version_id)
    if version is None or version.section_id != section_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Version not found")

    success = await version_store.delete(version_id)
    if not success:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Cannot delete the last version of a section",
        )

    logger.info(f"Deleted version {version_id}")


@router.post("/{version_id}/duplicate", response_model=SectionVersionResponse, status_code=status.HTTP_201_CREATED)
async def duplicate_version(
    song_id: UUID,
    section_id: UUID,
    version_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    name: Optional[str] = None,
    store: SongDBStore = Depends(get_db_store),
    version_store: SectionVersionStore = Depends(get_version_store),
):
    """Duplicate a version with all its lines."""
    await verify_song_and_section(
        song_id, section_id, user.id, Permission.WRITE, store, permission_service
    )

    version = await version_store.get(version_id)
    if version is None or version.section_id != section_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Version not found")

    new_version = await version_store.duplicate(version_id, name=name)
    if new_version is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to duplicate version")

    logger.info(f"Duplicated version {version_id} -> {new_version.id}")
    return SectionVersionResponse.from_version(new_version)


@router.post("/{version_id}/promote", response_model=SectionVersionResponse)
async def promote_version(
    song_id: UUID,
    section_id: UUID,
    version_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    store: SongDBStore = Depends(get_db_store),
    version_store: SectionVersionStore = Depends(get_version_store),
):
    """Promote a version to be the main version."""
    await verify_song_and_section(
        song_id, section_id, user.id, Permission.WRITE, store, permission_service
    )

    version = await version_store.get(version_id)
    if version is None or version.section_id != section_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Version not found")

    version = await version_store.promote_to_main(version_id)

    logger.info(f"Promoted version {version_id} to main")
    return SectionVersionResponse.from_version(version)
