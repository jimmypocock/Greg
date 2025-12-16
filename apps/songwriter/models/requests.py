"""Request schemas for Songwriter API."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from apps.songwriter.enums import NoteType, SectionType, SongStatus


# Simple Pydantic models for API requests (not database models)

class ChordPlacementRequest(BaseModel):
    """A chord placement in an API request."""

    chord: str = Field(..., description="Chord symbol (e.g., 'G', 'Cmaj7', 'F#m')")
    position: int = Field(..., ge=0, description="Character index where chord lands")


class LineRequest(BaseModel):
    """A line of lyrics in an API request."""

    text: str = Field(default="", description="The lyric text")
    chords: list[ChordPlacementRequest] = Field(default_factory=list)
    notes: Optional[str] = None


class Section(BaseModel):
    """A section in a structure suggestion (Pydantic, not database model)."""

    type: SectionType
    number: Optional[int] = None
    lines: list[LineRequest] = Field(default_factory=list)
    notes: Optional[str] = None


class SongCreateRequest(BaseModel):
    """Request to create a new song from raw input."""

    title: str = Field(..., min_length=1, max_length=200)
    raw_input: str = Field(..., min_length=1, description="Raw lyrics/notes to structure")
    key: Optional[str] = None
    tempo: Optional[int] = Field(None, ge=20, le=300)
    time_signature: str = Field(default="4/4")
    feel: Optional[str] = None
    notes: Optional[str] = None


class SongUpdateRequest(BaseModel):
    """Request to update song metadata."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    key: Optional[str] = None
    tempo: Optional[int] = Field(None, ge=20, le=300)
    time_signature: Optional[str] = None
    feel: Optional[str] = None
    status: Optional[SongStatus] = None
    notes: Optional[str] = None


class AddChordRequest(BaseModel):
    """Request to add a chord to a line."""

    section_id: UUID
    line_id: UUID
    chord: str
    position: int = Field(..., ge=0)


class SectionUpdateRequest(BaseModel):
    """Request to update a section."""

    type: Optional[SectionType] = None
    number: Optional[int] = None
    notes: Optional[str] = None


class StructureSuggestion(BaseModel):
    """AI-suggested structure for raw lyrics."""

    sections: list[Section]
    confidence: float = Field(..., ge=0, le=1, description="Confidence in the suggestion")
    reasoning: Optional[str] = Field(None, description="Explanation of the structure")


# Song notes requests

class SongNoteCreateRequest(BaseModel):
    """Request to create a new song note."""

    note_type: NoteType = Field(default=NoteType.IDEA)
    content: str = Field(..., min_length=1)
    title: Optional[str] = Field(None, max_length=200)
    section_id: Optional[UUID] = None


class SongNoteUpdateRequest(BaseModel):
    """Request to update a song note."""

    note_type: Optional[NoteType] = None
    content: Optional[str] = None
    title: Optional[str] = None
    is_resolved: Optional[bool] = None
