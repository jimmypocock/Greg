"""
Song routes for the Songwriter app.

Endpoints:
    POST   /songs              - Create a new song
    GET    /songs              - List all songs
    GET    /songs/{id}         - Get a song by ID
    PUT    /songs/{id}         - Update a song
    DELETE /songs/{id}         - Delete a song
    POST   /songs/{id}/suggest-structure - Get AI structure suggestion
    POST   /songs/{id}/apply-structure   - Apply a structure to the song
    POST   /songs/{id}/chords            - Add a chord to a line
    DELETE /songs/{id}/chords            - Remove a chord from a line
    GET    /songs/{id}/chord-sheet       - Get text chord sheet
"""

import logging
from datetime import datetime
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.auth import CurrentUser
from packages.core.database import get_session_dependency

from apps.songwriter.enums import AgentTaskType, AgentType, CollaboratorRole, SectionType, SongStatus
from apps.songwriter.models import (
    AddChordRequest,
    ChordPlacement,
    Line,
    SectionVersion,
    Song,
    SongCollaborator,
    SongCreateRequest,
    SongSection,
    SongUpdateRequest,
    StructureSuggestion,
)
from apps.songwriter.services import get_structure_service, parse_markdown
from apps.songwriter.services.db_store import SongDBStore
from apps.songwriter.services.agent_review_store import AgentReviewStore
from apps.songwriter.services.permissions import Permission, SongPermissionService
from apps.songwriter.services.version_store import SectionVersionStore
from apps.songwriter.dependencies import PermissionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/songs", tags=["Songs"])


# Dependency for getting a song store with session
async def get_db_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> SongDBStore:
    """Get a database-backed song store."""
    return SongDBStore(session)


# Dependency for getting a review store
async def get_review_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> AgentReviewStore:
    """Get an agent review store."""
    return AgentReviewStore(session)


# Dependency for getting a version store
async def get_version_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> SectionVersionStore:
    """Get a section version store."""
    return SectionVersionStore(session)


# Response models

class ChordResponse(BaseModel):
    """Chord placement response for API."""

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


class SectionVersionSummary(BaseModel):
    """Summary of a section version."""

    id: UUID
    version_number: int
    name: Optional[str]
    is_main: bool
    line_count: int

    model_config = {"from_attributes": True}


class SongSectionResponse(BaseModel):
    """SongSection response for API."""

    id: UUID
    song_id: UUID
    type: SectionType
    number: Optional[int]
    order: int
    notes: Optional[str]
    lines: list[LineResponse]
    versions: list[SectionVersionSummary]
    main_version_id: Optional[UUID]
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_section(cls, section: SongSection) -> "SongSectionResponse":
        """Convert a SongSection model to a response."""
        # Get main version and its lines
        main_version = section.main_version
        lines = main_version.lines if main_version else []
        sorted_lines = sorted(lines, key=lambda l: l.order)

        # Build version summaries
        version_summaries = [
            SectionVersionSummary(
                id=v.id,
                version_number=v.version_number,
                name=v.name,
                is_main=v.is_main,
                line_count=len(v.lines) if v.lines else 0,
            )
            for v in sorted(section.versions, key=lambda v: v.version_number)
        ]

        return cls(
            id=section.id,
            song_id=section.song_id,
            type=section.type,
            number=section.number,
            order=section.order,
            notes=section.notes,
            lines=[LineResponse.from_line(line) for line in sorted_lines],
            versions=version_summaries,
            main_version_id=main_version.id if main_version else None,
            created_at=section.created_at,
        )


class SongResponse(BaseModel):
    """Full song response including sections."""

    id: UUID
    title: str
    raw_input: Optional[str]
    key: Optional[str]
    tempo: Optional[int]
    time_signature: str
    feel: Optional[str]
    status: SongStatus
    notes: Optional[str]
    owner_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    sections: list[SongSectionResponse] = []

    @classmethod
    def from_song(cls, song: Song) -> "SongResponse":
        """Convert a Song model to a response."""
        # Sort sections by order to ensure proper display
        sorted_sections = sorted(song.sections, key=lambda s: s.order)
        return cls(
            id=song.id,
            title=song.title,
            raw_input=song.raw_input,
            key=song.key,
            tempo=song.tempo,
            time_signature=song.time_signature,
            feel=song.feel,
            status=song.status,
            notes=song.notes,
            owner_id=song.owner_id,
            created_at=song.created_at,
            updated_at=song.updated_at,
            sections=[SongSectionResponse.from_section(s) for s in sorted_sections],
        )


class SongListItem(BaseModel):
    """Summary of a song for list views."""

    id: UUID
    title: str
    status: SongStatus
    key: Optional[str]
    tempo: Optional[int]
    section_count: int
    created_at: datetime
    updated_at: datetime


class SongListResponse(BaseModel):
    """Response for listing songs."""

    songs: list[SongListItem]
    total: int


class ApplyStructureRequest(BaseModel):
    """Request to apply a structure to a song."""

    sections: list[dict]  # Section data as dicts


class RemoveChordRequest(BaseModel):
    """Request to remove a chord from a line."""

    section_id: UUID
    line_id: UUID
    position: int


class UpdateLineRequest(BaseModel):
    """Request to update a line's text."""

    section_id: UUID
    line_id: UUID
    text: str


class AddLineRequest(BaseModel):
    """Request to add a new line to a section."""

    section_id: UUID
    text: str
    after_line_id: Optional[UUID] = None  # Insert after this line, or at end if None


class AddSectionRequest(BaseModel):
    """Request to add a new section."""

    type: SectionType
    number: Optional[int] = None
    after_section_id: Optional[UUID] = None  # Insert after this section, or at end


# Routes

@router.post("/", response_model=SongResponse, status_code=status.HTTP_201_CREATED)
async def create_song(
    request: SongCreateRequest,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Create a new song from raw input.

    The raw_input is preserved and can be used later for AI structuring.
    The authenticated user becomes the owner of the song.

    A new song starts with a single BRAIN_DUMP section for unstructured content.
    This allows users to brainstorm before structuring their song.
    """
    song = Song(
        title=request.title,
        raw_input=request.raw_input,
        key=request.key,
        tempo=request.tempo,
        time_signature=request.time_signature,
        feel=request.feel,
        notes=request.notes,
        status=SongStatus.IDEA,
        owner_id=user.id,
    )

    song = await store.create(song)

    # Create owner collaborator record
    from apps.songwriter.models.utils import utc_now
    collaborator = SongCollaborator(
        song_id=song.id,
        user_id=user.id,
        role=CollaboratorRole.OWNER,
        invited_by=None,
        accepted_at=utc_now(),
    )
    session.add(collaborator)
    await session.commit()

    # Auto-create a BRAIN_DUMP section for brainstorming
    brain_dump_section = SongSection(
        song_id=song.id,
        type=SectionType.BRAIN_DUMP,
        order=0,
    )
    await store.add_section(song.id, brain_dump_section)

    # Add initial line (empty or from raw_input if provided)
    initial_text = request.raw_input or ""
    initial_line = Line(text=initial_text, order=0)
    await store.add_line(brain_dump_section.id, initial_line)

    # Refresh song to include the new section
    song = await store.get(song.id)

    logger.info(f"Created song: {song.title} ({song.id}) by user {user.email}")

    return SongResponse.from_song(song)


class MarkdownInput(BaseModel):
    """Markdown content to parse into a song."""

    content: str = Field(..., description="Markdown content with # Title and optional ## Sections")


@router.post("/from-markdown", response_model=SongResponse, status_code=status.HTTP_201_CREATED)
async def create_song_from_markdown(
    request: MarkdownInput,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Create a song from markdown content.

    Format:
        # Song Title

        ## Verse
        First line
        Second line

        ## Chorus
        Chorus lyrics

    If no ## section headers are provided, the lyrics are stored as raw_input
    and can be structured later with AI via /suggest-structure.
    """
    song = parse_markdown(request.content)
    song.owner_id = user.id
    song = await store.create(song)

    # Create owner collaborator record
    from apps.songwriter.models.utils import utc_now
    collaborator = SongCollaborator(
        song_id=song.id,
        user_id=user.id,
        role=CollaboratorRole.OWNER,
        invited_by=None,
        accepted_at=utc_now(),
    )
    session.add(collaborator)
    await session.commit()

    section_info = f"{len(song.sections)} sections" if song.sections else "unstructured"
    logger.info(f"Created song from markdown: {song.title} ({section_info}) by user {user.email}")

    return SongResponse.from_song(song)


@router.get("/", response_model=SongListResponse)
async def list_songs(
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
    limit: int = Query(50, ge=1, le=100, description="Maximum songs to return"),
    offset: int = Query(0, ge=0, description="Number of songs to skip"),
):
    """List songs the user has access to (owned or collaborated).

    Args:
        limit: Maximum number of songs to return (1-100, default 50)
        offset: Number of songs to skip (default 0)
    """
    # Get songs where user is owner or collaborator
    # Build subquery for collaborator song IDs
    collab_song_ids = select(SongCollaborator.song_id).where(
        SongCollaborator.user_id == user.id
    )

    # Query songs user can access
    query = (
        select(Song)
        .where(
            or_(
                Song.owner_id == user.id,
                Song.id.in_(collab_song_ids),
            )
        )
        .order_by(Song.updated_at.desc())
    )

    # Get total count
    from sqlalchemy import func
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await session.execute(count_query)
    total = count_result.scalar() or 0

    # Get paginated results with relationships loaded
    from sqlalchemy.orm import selectinload
    paginated_query = (
        query
        .options(selectinload(Song.sections))
        .limit(limit)
        .offset(offset)
    )
    result = await session.execute(paginated_query)
    songs = list(result.scalars().all())

    return SongListResponse(
        songs=[
            SongListItem(
                id=s.id,
                title=s.title,
                status=s.status,
                key=s.key,
                tempo=s.tempo,
                section_count=len(s.sections),
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
            for s in songs
        ],
        total=total,
    )


@router.get("/{song_id}", response_model=SongResponse)
async def get_song(
    song_id: UUID,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    perm_service: PermissionService,
):
    """Get a song by ID. Requires read access."""
    await perm_service.require_permission(song_id, user.id, Permission.READ)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    return SongResponse.from_song(song)


@router.put("/{song_id}", response_model=SongResponse)
async def update_song(
    song_id: UUID,
    request: SongUpdateRequest,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    perm_service: PermissionService,
):
    """Update song metadata. Requires write access."""
    await perm_service.require_permission(song_id, user.id, Permission.WRITE)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    # Build updates dict from request
    updates = {}
    if request.title is not None:
        updates["title"] = request.title
    if request.key is not None:
        updates["key"] = request.key
    if request.tempo is not None:
        updates["tempo"] = request.tempo
    if request.time_signature is not None:
        updates["time_signature"] = request.time_signature
    if request.feel is not None:
        updates["feel"] = request.feel
    if request.status is not None:
        updates["status"] = request.status
    if request.notes is not None:
        updates["notes"] = request.notes

    song = await store.update(song_id, updates)
    logger.info(f"Updated song: {song.title} ({song.id}) by user {user.email}")

    return SongResponse.from_song(song)


@router.delete("/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_song(
    song_id: UUID,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    perm_service: PermissionService,
):
    """Delete a song. Requires admin (owner) access."""
    await perm_service.require_permission(song_id, user.id, Permission.ADMIN)

    if not await store.delete(song_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    logger.info(f"Deleted song: {song_id} by user {user.email}")


@router.post("/{song_id}/suggest-structure", response_model=StructureSuggestion)
async def suggest_structure(
    song_id: UUID,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    review_store: Annotated[AgentReviewStore, Depends(get_review_store)],
    perm_service: PermissionService,
):
    """
    Get AI-suggested structure for a song's raw input.

    Does not modify the song - returns a suggestion that can be applied separately.
    Also saves the analysis to review history. Requires read access.
    """
    await perm_service.require_permission(song_id, user.id, Permission.READ)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    if not song.raw_input:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Song has no raw input to analyze",
        )

    structure_service = get_structure_service()
    suggestion = await structure_service.suggest_structure(song.raw_input)

    # Build a formatted result for review history
    section_summary = ", ".join(
        f"{s.type.value}{' ' + str(s.number) if s.number else ''} ({len(s.lines)} lines)"
        for s in suggestion.sections
    )
    review_result = f"""## Structure Analysis

**Confidence:** {suggestion.confidence:.0%}

**Suggested Structure:** {section_summary}

**Reasoning:** {suggestion.reasoning or 'No reasoning provided.'}"""

    # Save to review history
    await review_store.create(
        song_id=song_id,
        agent_type=AgentType.STRUCTURE,
        task_type=AgentTaskType.STRUCTURE_ANALYSIS,
        result=review_result,
        input_tokens=0,  # Not tracked for this simple call
        output_tokens=0,
        success=True,
    )

    logger.info(f"Generated structure suggestion for song: {song.title} (confidence: {suggestion.confidence})")

    return suggestion


@router.post("/{song_id}/apply-structure", response_model=SongResponse)
async def apply_structure(
    song_id: UUID,
    request: ApplyStructureRequest,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    perm_service: PermissionService,
):
    """
    Apply a structure (sections) to a song.

    This replaces any existing sections. Requires write access.
    """
    await perm_service.require_permission(song_id, user.id, Permission.WRITE)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    # Delete existing sections first
    for section in list(song.sections):
        await store.delete_section(section.id)

    # Create new sections, then add lines to each section
    for i, section_data in enumerate(request.sections):
        # Create section without lines first
        section = SongSection(
            song_id=song_id,
            type=SectionType(section_data["type"]),
            number=section_data.get("number"),
            order=i,
            notes=section_data.get("notes"),
        )
        await store.add_section(song_id, section)

        # Now add lines to the section
        for j, line_data in enumerate(section_data.get("lines", [])):
            line_text = line_data.get("text", "") if isinstance(line_data, dict) else str(line_data)
            line = Line(text=line_text, order=j)
            await store.add_line(section.id, line)

    await store.update(song_id, {"status": SongStatus.DRAFT})
    song = await store.get(song_id)

    logger.info(f"Applied structure to song: {song.title} ({len(request.sections)} sections)")

    return SongResponse.from_song(song)


@router.post("/{song_id}/chords", response_model=SongResponse)
async def add_chord(
    song_id: UUID,
    request: AddChordRequest,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    perm_service: PermissionService,
):
    """Add a chord to a specific position in a line. Requires write access."""
    await perm_service.require_permission(song_id, user.id, Permission.WRITE)

    # Verify ownership with a single efficient query
    if not await store.verify_line_ownership(song_id, request.section_id, request.line_id):
        # Determine which entity is missing for the error message
        song = await store.get(song_id)
        if not song:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Song not found: {song_id}")
        if not await store.verify_section_ownership(song_id, request.section_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Section not found: {request.section_id}")
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Line not found: {request.line_id}")

    # Check if chord exists at this position
    existing = await store.get_chord_by_position(request.line_id, request.position)
    if existing:
        # Update existing chord
        await store.update_chord(existing.id, {"chord": request.chord})
    else:
        # Add new chord
        chord = ChordPlacement(
            line_id=request.line_id,
            chord=request.chord,
            position=request.position,
        )
        await store.add_chord(request.line_id, chord)

    # Return updated song
    song = await store.get(song_id)
    return SongResponse.from_song(song)


@router.delete("/{song_id}/chords", response_model=SongResponse)
async def remove_chord(
    song_id: UUID,
    request: RemoveChordRequest,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    perm_service: PermissionService,
):
    """Remove a chord from a specific position in a line. Requires write access."""
    await perm_service.require_permission(song_id, user.id, Permission.WRITE)

    # Verify ownership with a single efficient query
    if not await store.verify_line_ownership(song_id, request.section_id, request.line_id):
        song = await store.get(song_id)
        if not song:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Song not found: {song_id}")
        if not await store.verify_section_ownership(song_id, request.section_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Section not found: {request.section_id}")
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Line not found: {request.line_id}")

    # Find and delete chord at this position
    chord_to_delete = await store.get_chord_by_position(request.line_id, request.position)
    if chord_to_delete:
        await store.delete_chord(chord_to_delete.id)

    song = await store.get(song_id)
    return SongResponse.from_song(song)


@router.get("/{song_id}/chord-sheet", response_model=str)
async def get_chord_sheet(
    song_id: UUID,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    perm_service: PermissionService,
):
    """Get a text-formatted chord sheet for printing/export. Requires read access."""
    await perm_service.require_permission(song_id, user.id, Permission.READ)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    return song.get_chord_sheet()


@router.post("/{song_id}/lines", response_model=SongResponse)
async def add_line(
    song_id: UUID,
    request: AddLineRequest,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    perm_service: PermissionService,
):
    """Add a new line to a section. Requires write access."""
    await perm_service.require_permission(song_id, user.id, Permission.WRITE)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    # Verify section belongs to this song
    section = next(
        (s for s in song.sections if s.id == request.section_id),
        None
    )
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section not found: {request.section_id}",
        )

    # Create new line with proper order
    new_line = Line(section_id=request.section_id, text=request.text)
    await store.add_line(
        request.section_id,
        new_line,
        after_line_id=request.after_line_id,
    )

    song = await store.get(song_id)
    return SongResponse.from_song(song)


@router.put("/{song_id}/lines", response_model=SongResponse)
async def update_line(
    song_id: UUID,
    request: UpdateLineRequest,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    perm_service: PermissionService,
):
    """Update a line's text. Requires write access."""
    await perm_service.require_permission(song_id, user.id, Permission.WRITE)

    # Verify ownership with a single efficient query
    if not await store.verify_line_ownership(song_id, request.section_id, request.line_id):
        song = await store.get(song_id)
        if not song:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Song not found: {song_id}")
        if not await store.verify_section_ownership(song_id, request.section_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Section not found: {request.section_id}")
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Line not found: {request.line_id}")

    await store.update_line(request.line_id, {"text": request.text})
    song = await store.get(song_id)
    return SongResponse.from_song(song)


@router.post("/{song_id}/sections", response_model=SongResponse)
async def add_section(
    song_id: UUID,
    request: AddSectionRequest,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    perm_service: PermissionService,
):
    """Add a new section to the song. Requires write access."""
    await perm_service.require_permission(song_id, user.id, Permission.WRITE)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    new_section = SongSection(
        type=request.type,
        number=request.number,
        song_id=song_id,
    )

    await store.add_section(song_id, new_section, after_section_id=request.after_section_id)

    song = await store.get(song_id)
    return SongResponse.from_song(song)


class ReorderSectionsRequest(BaseModel):
    """Request to reorder sections."""

    section_ids: list[UUID] = Field(..., description="Section IDs in the new order")


# NOTE: This route MUST come before /{song_id}/sections/{section_id} to avoid
# "reorder" being matched as a section_id
@router.put("/{song_id}/sections/reorder", response_model=SongResponse)
async def reorder_sections(
    song_id: UUID,
    request: ReorderSectionsRequest,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    perm_service: PermissionService,
):
    """Reorder sections in a song. Requires write access."""
    await perm_service.require_permission(song_id, user.id, Permission.WRITE)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    # Verify all section IDs belong to this song
    song_section_ids = {s.id for s in song.sections}
    if set(request.section_ids) != song_section_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Section IDs don't match the song's sections",
        )

    # Update order for each section
    for new_order, section_id in enumerate(request.section_ids):
        await store.update_section(section_id, {"order": new_order})

    song = await store.get(song_id)
    logger.info(f"Reordered sections in song: {song.title}")
    return SongResponse.from_song(song)


class UpdateSectionRequest(BaseModel):
    """Request to update a section."""

    type: SectionType | None = Field(None, description="New section type")
    number: int | None = Field(None, description="New section number")


@router.put("/{song_id}/sections/{section_id}", response_model=SongResponse)
async def update_section(
    song_id: UUID,
    section_id: UUID,
    request: UpdateSectionRequest,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    perm_service: PermissionService,
):
    """Update a section's type or number. Requires write access."""
    await perm_service.require_permission(song_id, user.id, Permission.WRITE)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    # Verify section belongs to this song
    section = next((s for s in song.sections if s.id == section_id), None)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section not found: {section_id}",
        )

    # Build update dict with only provided fields
    updates = {}
    if request.type is not None:
        updates["type"] = request.type
    if request.number is not None:
        updates["number"] = request.number

    if updates:
        await store.update_section(section_id, updates)
        logger.info(f"Updated section {section_id} in song: {song.title}")

    song = await store.get(song_id)
    return SongResponse.from_song(song)


class DeleteLineRequest(BaseModel):
    """Request to delete a line."""

    section_id: UUID
    line_id: UUID


@router.delete("/{song_id}/lines", response_model=SongResponse)
async def delete_line(
    song_id: UUID,
    request: DeleteLineRequest,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    perm_service: PermissionService,
):
    """Delete a line from a section. Requires write access."""
    await perm_service.require_permission(song_id, user.id, Permission.WRITE)

    # Verify ownership with a single efficient query
    if not await store.verify_line_ownership(song_id, request.section_id, request.line_id):
        song = await store.get(song_id)
        if not song:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Song not found: {song_id}")
        if not await store.verify_section_ownership(song_id, request.section_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Section not found: {request.section_id}")
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Line not found: {request.line_id}")

    await store.delete_line(request.line_id)
    song = await store.get(song_id)
    return SongResponse.from_song(song)


class ReorderLinesRequest(BaseModel):
    """Request to reorder lines within a section."""

    section_id: UUID
    line_ids: list[UUID] = Field(..., description="Line IDs in the new order")


@router.put("/{song_id}/lines/reorder", response_model=SongResponse)
async def reorder_lines(
    song_id: UUID,
    request: ReorderLinesRequest,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    perm_service: PermissionService,
):
    """Reorder lines within a section. Requires write access."""
    await perm_service.require_permission(song_id, user.id, Permission.WRITE)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    # Find the section
    section = next(
        (s for s in song.sections if s.id == request.section_id),
        None
    )
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section not found: {request.section_id}",
        )

    # Verify all line IDs belong to this section
    section_line_ids = {line.id for line in section.lines}
    if set(request.line_ids) != section_line_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Line IDs don't match the section's lines",
        )

    # Update order for each line
    for new_order, line_id in enumerate(request.line_ids):
        await store.update_line(line_id, {"order": new_order})

    song = await store.get(song_id)
    logger.info(f"Reordered lines in section of song: {song.title}")
    return SongResponse.from_song(song)


@router.delete("/{song_id}/sections/{section_id}", response_model=SongResponse)
async def delete_section(
    song_id: UUID,
    section_id: UUID,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    perm_service: PermissionService,
):
    """Delete a section from a song. Requires write access."""
    await perm_service.require_permission(song_id, user.id, Permission.WRITE)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    # Verify section belongs to this song
    section = next(
        (s for s in song.sections if s.id == section_id),
        None
    )
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section not found: {section_id}",
        )

    await store.delete_section(section_id)
    song = await store.get(song_id)
    logger.info(f"Deleted section from song: {song.title}")
    return SongResponse.from_song(song)


class StructureBrainDumpRequest(BaseModel):
    """Request to structure brain dump content using AI."""

    llm: Optional[str] = Field(
        None,
        description="LLM to use (e.g., 'ollama/mistral'). Uses default if not specified.",
    )


class StructuredVersionResponse(BaseModel):
    """Response after structuring brain dump content."""

    version_id: UUID
    version_number: int
    sections_created: int
    message: str


@router.post(
    "/{song_id}/sections/{section_id}/structure",
    response_model=StructuredVersionResponse,
)
async def structure_brain_dump(
    song_id: UUID,
    section_id: UUID,
    request: StructureBrainDumpRequest,
    user: CurrentUser,
    store: Annotated[SongDBStore, Depends(get_db_store)],
    version_store: Annotated[SectionVersionStore, Depends(get_version_store)],
    review_store: Annotated[AgentReviewStore, Depends(get_review_store)],
    perm_service: PermissionService,
):
    """
    Structure brain dump content using AI.

    Takes the content from a BRAIN_DUMP section and uses AI to suggest a structure.
    Creates a NEW VERSION of the section with the structured content, preserving
    the original unstructured content as version 1.

    This allows users to:
    1. Keep their original brain dump for reference
    2. Review the AI's suggested structure
    3. Switch between versions to compare
    4. Edit the structured version without losing the original

    Requires write access.
    """
    await perm_service.require_permission(song_id, user.id, Permission.WRITE)

    song = await store.get(song_id)
    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    # Find the section
    section = next((s for s in song.sections if s.id == section_id), None)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section not found: {section_id}",
        )

    # Verify it's a BRAIN_DUMP section
    if section.type != SectionType.BRAIN_DUMP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Section must be a BRAIN_DUMP section to structure. Got: {section.type.value}",
        )

    # Get the current (main) version's content
    main_version = section.main_version
    if not main_version or not main_version.lines:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Section has no content to structure",
        )

    # Combine all lines into raw text
    raw_content = "\n".join(line.text for line in sorted(main_version.lines, key=lambda l: l.order))

    if not raw_content.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Section content is empty",
        )

    # Call AI to structure the content
    structure_service = get_structure_service()
    suggestion = await structure_service.suggest_structure(raw_content)

    # Create a new version with structured content
    # The version will contain lines formatted with section markers
    new_version = await version_store.create(
        section_id=section_id,
        name=f"AI Structured ({suggestion.confidence:.0%} confidence)",
        is_main=False,  # Don't make it main automatically - let user decide
    )

    # Build structured content as lines
    # Format: section headers followed by lines
    line_order = 0
    sections_created = 0

    for suggested_section in suggestion.sections:
        # Add section header line
        section_name = suggested_section.type.value.title()
        if suggested_section.number:
            section_name += f" {suggested_section.number}"

        header_line = Line(
            version_id=new_version.id,
            text=f"[{section_name}]",
            order=line_order,
        )
        await version_store.add_line(new_version.id, header_line)
        line_order += 1

        # Add content lines
        for suggested_line in suggested_section.lines:
            content_line = Line(
                version_id=new_version.id,
                text=suggested_line.text,
                order=line_order,
            )
            await version_store.add_line(new_version.id, content_line)
            line_order += 1

        # Add empty line between sections for readability
        spacer_line = Line(
            version_id=new_version.id,
            text="",
            order=line_order,
        )
        await version_store.add_line(new_version.id, spacer_line)
        line_order += 1
        sections_created += 1

    # Save to review history
    section_summary = ", ".join(
        f"{s.type.value}{' ' + str(s.number) if s.number else ''}"
        for s in suggestion.sections
    )
    review_result = f"""## Brain Dump Structure Analysis

**Input:** {len(raw_content)} characters

**Confidence:** {suggestion.confidence:.0%}

**Suggested Structure:** {section_summary}

**Reasoning:** {suggestion.reasoning or 'No reasoning provided.'}

**Version Created:** {new_version.version_number}"""

    await review_store.create(
        song_id=song_id,
        agent_type=AgentType.STRUCTURE,
        task_type=AgentTaskType.STRUCTURE_ANALYSIS,
        result=review_result,
        input_tokens=0,
        output_tokens=0,
        success=True,
    )

    logger.info(
        f"Structured brain dump for song {song.title}: "
        f"{sections_created} sections, version {new_version.version_number}"
    )

    return StructuredVersionResponse(
        version_id=new_version.id,
        version_number=new_version.version_number,
        sections_created=sections_created,
        message=f"Created structured version with {sections_created} sections. "
        f"Review and promote to main when ready.",
    )
