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

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from apps.songwriter.enums import SectionType, SongStatus
from apps.songwriter.models import (
    AddChordRequest,
    ChordPlacement,
    Line,
    Song,
    SongCreateRequest,
    SongSection,
    SongUpdateRequest,
    StructureSuggestion,
)
from apps.songwriter.services import get_structure_service, parse_markdown
from apps.songwriter.services.db_store import SongDBStore
from packages.core.database import get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/songs", tags=["Songs"])


# Dependency for getting a song store with session
async def get_db_store(
    session: Annotated[AsyncSession, Depends(get_session_dependency)]
) -> SongDBStore:
    """Get a database-backed song store."""
    return SongDBStore(session)


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


class SongSectionResponse(BaseModel):
    """SongSection response for API."""

    id: UUID
    song_id: UUID
    type: SectionType
    number: Optional[int]
    order: int
    notes: Optional[str]
    lines: list[LineResponse]
    created_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_section(cls, section: SongSection) -> "SongSectionResponse":
        """Convert a SongSection model to a response."""
        # Sort lines by order to ensure proper display
        sorted_lines = sorted(section.lines, key=lambda l: l.order)
        return cls(
            id=section.id,
            song_id=section.song_id,
            type=section.type,
            number=section.number,
            order=section.order,
            notes=section.notes,
            lines=[LineResponse.from_line(line) for line in sorted_lines],
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
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """
    Create a new song from raw input.

    The raw_input is preserved and can be used later for AI structuring.
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
    )

    song = await store.create(song)
    logger.info(f"Created song: {song.title} ({song.id})")

    return SongResponse.from_song(song)


class MarkdownInput(BaseModel):
    """Markdown content to parse into a song."""

    content: str = Field(..., description="Markdown content with # Title and optional ## Sections")


@router.post("/from-markdown", response_model=SongResponse, status_code=status.HTTP_201_CREATED)
async def create_song_from_markdown(
    request: MarkdownInput,
    store: Annotated[SongDBStore, Depends(get_db_store)],
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
    song = await store.create(song)

    section_info = f"{len(song.sections)} sections" if song.sections else "unstructured"
    logger.info(f"Created song from markdown: {song.title} ({section_info})")

    return SongResponse.from_song(song)


@router.get("/", response_model=SongListResponse)
async def list_songs(
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """List all songs."""
    songs = await store.list_all()

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
        total=len(songs),
    )


@router.get("/{song_id}", response_model=SongResponse)
async def get_song(
    song_id: UUID,
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """Get a song by ID."""
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
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """Update song metadata."""
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
    logger.info(f"Updated song: {song.title} ({song.id})")

    return SongResponse.from_song(song)


@router.delete("/{song_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_song(
    song_id: UUID,
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """Delete a song."""
    if not await store.delete(song_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    logger.info(f"Deleted song: {song_id}")


@router.post("/{song_id}/suggest-structure", response_model=StructureSuggestion)
async def suggest_structure(
    song_id: UUID,
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """
    Get AI-suggested structure for a song's raw input.

    Does not modify the song - returns a suggestion that can be applied separately.
    """
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

    logger.info(f"Generated structure suggestion for song: {song.title} (confidence: {suggestion.confidence})")

    return suggestion


@router.post("/{song_id}/apply-structure", response_model=SongResponse)
async def apply_structure(
    song_id: UUID,
    request: ApplyStructureRequest,
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """
    Apply a structure (sections) to a song.

    This replaces any existing sections.
    """
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
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """Add a chord to a specific position in a line."""
    song = await store.get(song_id)

    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    # Verify section and line belong to this song
    line_found = False
    for section in song.sections:
        if section.id == request.section_id:
            for line in section.lines:
                if line.id == request.line_id:
                    line_found = True
                    # Check if chord exists at this position
                    existing = next(
                        (c for c in line.chords if c.position == request.position),
                        None
                    )
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
                    break
            if not line_found:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Line not found: {request.line_id}",
                )
            break
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Section not found: {request.section_id}",
        )

    # Return updated song
    song = await store.get(song_id)
    return SongResponse.from_song(song)


@router.delete("/{song_id}/chords", response_model=SongResponse)
async def remove_chord(
    song_id: UUID,
    request: RemoveChordRequest,
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """Remove a chord from a specific position in a line."""
    song = await store.get(song_id)

    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    for section in song.sections:
        if section.id == request.section_id:
            for line in section.lines:
                if line.id == request.line_id:
                    # Find and delete chord at this position
                    chord_to_delete = next(
                        (c for c in line.chords if c.position == request.position),
                        None
                    )
                    if chord_to_delete:
                        await store.delete_chord(chord_to_delete.id)

                    song = await store.get(song_id)
                    return SongResponse.from_song(song)

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Line not found: {request.line_id}",
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Section not found: {request.section_id}",
    )


@router.get("/{song_id}/chord-sheet", response_model=str)
async def get_chord_sheet(
    song_id: UUID,
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """Get a text-formatted chord sheet for printing/export."""
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
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """Add a new line to a section."""
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
    await store.add_line(request.section_id, new_line)

    # TODO: Handle after_line_id for insertion ordering if needed

    song = await store.get(song_id)
    return SongResponse.from_song(song)


@router.put("/{song_id}/lines", response_model=SongResponse)
async def update_line(
    song_id: UUID,
    request: UpdateLineRequest,
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """Update a line's text."""
    song = await store.get(song_id)

    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    # Verify section and line belong to this song
    for section in song.sections:
        if section.id == request.section_id:
            for line in section.lines:
                if line.id == request.line_id:
                    await store.update_line(request.line_id, {"text": request.text})
                    song = await store.get(song_id)
                    return SongResponse.from_song(song)

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Line not found: {request.line_id}",
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Section not found: {request.section_id}",
    )


@router.post("/{song_id}/sections", response_model=SongResponse)
async def add_section(
    song_id: UUID,
    request: AddSectionRequest,
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """Add a new section to the song."""
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

    await store.add_section(song_id, new_section)

    song = await store.get(song_id)
    return SongResponse.from_song(song)


class ReorderSectionsRequest(BaseModel):
    """Request to reorder sections."""

    section_ids: list[UUID] = Field(..., description="Section IDs in the new order")


@router.put("/{song_id}/sections/reorder", response_model=SongResponse)
async def reorder_sections(
    song_id: UUID,
    request: ReorderSectionsRequest,
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """Reorder sections in a song."""
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


class DeleteLineRequest(BaseModel):
    """Request to delete a line."""

    section_id: UUID
    line_id: UUID


@router.delete("/{song_id}/lines", response_model=SongResponse)
async def delete_line(
    song_id: UUID,
    request: DeleteLineRequest,
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """Delete a line from a section."""
    song = await store.get(song_id)

    if not song:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Song not found: {song_id}",
        )

    # Verify section and line belong to this song
    for section in song.sections:
        if section.id == request.section_id:
            for line in section.lines:
                if line.id == request.line_id:
                    await store.delete_line(request.line_id)
                    song = await store.get(song_id)
                    return SongResponse.from_song(song)

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Line not found: {request.line_id}",
            )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Section not found: {request.section_id}",
    )


class ReorderLinesRequest(BaseModel):
    """Request to reorder lines within a section."""

    section_id: UUID
    line_ids: list[UUID] = Field(..., description="Line IDs in the new order")


@router.put("/{song_id}/lines/reorder", response_model=SongResponse)
async def reorder_lines(
    song_id: UUID,
    request: ReorderLinesRequest,
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """Reorder lines within a section."""
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
    store: Annotated[SongDBStore, Depends(get_db_store)],
):
    """Delete a section from a song."""
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
