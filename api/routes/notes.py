"""
Song notes routes for the Songwriter app.

Brain dump notes, ideas, inspirations, and context for songs.

Endpoints:
    POST   /songs/{song_id}/notes      - Create a note for a song
    GET    /songs/{song_id}/notes      - List notes for a song
    GET    /songs/{song_id}/notes/{id} - Get a specific note
    PUT    /songs/{song_id}/notes/{id} - Update a note
    DELETE /songs/{song_id}/notes/{id} - Delete a note
    POST   /songs/{song_id}/notes/{id}/resolve   - Mark note as resolved
    POST   /songs/{song_id}/notes/{id}/unresolve - Mark note as unresolved
    GET    /songs/{song_id}/context    - Get all notes formatted for AI
"""

import logging
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import PermissionService
from api.enums import NoteType
from api.database.models import SongNote
from api.schemas import SongNoteCreateRequest, SongNoteUpdateRequest
from api.services.db_store import SongDBStore
from api.services.permissions import Permission
from api.services.song_note_store import SongNoteStore
from api.auth import CurrentUser
from api.database import get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/songs", tags=["Song Notes"])


# Dependencies

async def get_note_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> SongNoteStore:
    """Get a database-backed note store."""
    return SongNoteStore(session)


async def get_song_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> SongDBStore:
    """Get a database-backed song store."""
    return SongDBStore(session)


# Response models

class SongNoteResponse(BaseModel):
    """Response model for a song note."""

    id: UUID
    song_id: UUID
    section_id: Optional[UUID]
    note_type: NoteType
    title: Optional[str]
    content: str
    is_resolved: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SongNotesListResponse(BaseModel):
    """Response model for a list of notes."""

    notes: list[SongNoteResponse]
    total: int


class ContextResponse(BaseModel):
    """Response model for AI context."""

    context: str


# Routes

@router.post("/{song_id}/notes", response_model=SongNoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    song_id: UUID,
    request: SongNoteCreateRequest,
    user: CurrentUser,
    permission_service: PermissionService,
    note_store: Annotated[SongNoteStore, Depends(get_note_store)],
    song_store: Annotated[SongDBStore, Depends(get_song_store)],
):
    """Create a new note for a song."""
    # Check permission (raises 404 if song not found or no access, 403 if insufficient)
    await permission_service.require_permission(song_id, user.id, Permission.WRITE)

    # Verify song exists
    song = await song_store.get(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    # Verify section belongs to song if provided
    if request.section_id:
        section_found = any(s.id == request.section_id for s in song.sections)
        if not section_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Section not found: {request.section_id}",
            )

    note = SongNote(
        song_id=song_id,
        section_id=request.section_id,
        note_type=request.note_type,
        title=request.title,
        content=request.content,
    )

    note = await note_store.create(note)
    logger.info(f"Created note for song {song_id}: {note.note_type.value}")

    return SongNoteResponse.model_validate(note)


@router.get("/{song_id}/notes", response_model=SongNotesListResponse)
async def list_notes(
    song_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    note_store: Annotated[SongNoteStore, Depends(get_note_store)],
    song_store: Annotated[SongDBStore, Depends(get_song_store)],
    note_type: Optional[NoteType] = Query(None, description="Filter by note type"),
    include_resolved: bool = Query(True, description="Include resolved notes"),
    limit: int = Query(50, ge=1, le=100, description="Maximum notes to return"),
    offset: int = Query(0, ge=0, description="Number of notes to skip"),
):
    """List all notes for a song with pagination."""
    # Check permission (raises 404 if song not found or no access)
    await permission_service.require_permission(song_id, user.id, Permission.READ)

    # Verify song exists
    song = await song_store.get(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    notes, total = await note_store.list_by_song_paginated(
        song_id,
        note_type=note_type,
        include_resolved=include_resolved,
        limit=limit,
        offset=offset,
    )

    return SongNotesListResponse(
        notes=[SongNoteResponse.model_validate(n) for n in notes],
        total=total,
    )


@router.get("/{song_id}/notes/{note_id}", response_model=SongNoteResponse)
async def get_note(
    song_id: UUID,
    note_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    note_store: Annotated[SongNoteStore, Depends(get_note_store)],
):
    """Get a specific note."""
    # Check permission (raises 404 if song not found or no access)
    await permission_service.require_permission(song_id, user.id, Permission.READ)

    note = await note_store.get(note_id)

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note not found: {note_id}",
        )

    if note.song_id != song_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note not found: {note_id}",
        )

    return SongNoteResponse.model_validate(note)


@router.put("/{song_id}/notes/{note_id}", response_model=SongNoteResponse)
async def update_note(
    song_id: UUID,
    note_id: UUID,
    request: SongNoteUpdateRequest,
    user: CurrentUser,
    permission_service: PermissionService,
    note_store: Annotated[SongNoteStore, Depends(get_note_store)],
):
    """Update a note."""
    # Check permission (raises 404 if song not found or no access, 403 if insufficient)
    await permission_service.require_permission(song_id, user.id, Permission.WRITE)

    note = await note_store.get(note_id)

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note not found: {note_id}",
        )

    if note.song_id != song_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note not found: {note_id}",
        )

    # Build updates dict
    updates = {}
    if request.note_type is not None:
        updates["note_type"] = request.note_type
    if request.content is not None:
        updates["content"] = request.content
    if request.title is not None:
        updates["title"] = request.title
    if request.is_resolved is not None:
        updates["is_resolved"] = request.is_resolved

    if not updates:
        return SongNoteResponse.model_validate(note)

    note = await note_store.update(note_id, updates)
    logger.info(f"Updated note {note_id}")

    return SongNoteResponse.model_validate(note)


@router.delete("/{song_id}/notes/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    song_id: UUID,
    note_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    note_store: Annotated[SongNoteStore, Depends(get_note_store)],
):
    """Delete a note."""
    # Check permission (raises 404 if song not found or no access, 403 if insufficient)
    await permission_service.require_permission(song_id, user.id, Permission.WRITE)

    note = await note_store.get(note_id)

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note not found: {note_id}",
        )

    if note.song_id != song_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note not found: {note_id}",
        )

    await note_store.delete(note_id)
    logger.info(f"Deleted note {note_id}")


@router.post("/{song_id}/notes/{note_id}/resolve", response_model=SongNoteResponse)
async def resolve_note(
    song_id: UUID,
    note_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    note_store: Annotated[SongNoteStore, Depends(get_note_store)],
):
    """Mark a note as resolved (useful for TODOs)."""
    # Check permission (raises 404 if song not found or no access, 403 if insufficient)
    await permission_service.require_permission(song_id, user.id, Permission.WRITE)

    note = await note_store.get(note_id)

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note not found: {note_id}",
        )

    if note.song_id != song_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note not found: {note_id}",
        )

    note = await note_store.resolve(note_id)
    logger.info(f"Resolved note {note_id}")

    return SongNoteResponse.model_validate(note)


@router.post("/{song_id}/notes/{note_id}/unresolve", response_model=SongNoteResponse)
async def unresolve_note(
    song_id: UUID,
    note_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    note_store: Annotated[SongNoteStore, Depends(get_note_store)],
):
    """Mark a note as unresolved."""
    # Check permission (raises 404 if song not found or no access, 403 if insufficient)
    await permission_service.require_permission(song_id, user.id, Permission.WRITE)

    note = await note_store.get(note_id)

    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note not found: {note_id}",
        )

    if note.song_id != song_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Note not found: {note_id}",
        )

    note = await note_store.unresolve(note_id)
    logger.info(f"Unresolved note {note_id}")

    return SongNoteResponse.model_validate(note)


@router.get("/{song_id}/context", response_model=ContextResponse)
async def get_ai_context(
    song_id: UUID,
    user: CurrentUser,
    permission_service: PermissionService,
    note_store: Annotated[SongNoteStore, Depends(get_note_store)],
    song_store: Annotated[SongDBStore, Depends(get_song_store)],
):
    """Get all notes and context formatted for AI consumption."""
    # Check permission (raises 404 if song not found or no access)
    await permission_service.require_permission(song_id, user.id, Permission.READ)

    # Verify song exists
    song = await song_store.get(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    # Get song's own context method which includes quick notes and structured notes
    context = song.get_all_context()

    return ContextResponse(context=context)
