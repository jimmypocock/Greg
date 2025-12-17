"""Songwriter models."""

# SQLModel models (API + DB)
from apps.songwriter.models.agent_review import AgentReview
from apps.songwriter.models.audio_file import AudioFile
from apps.songwriter.models.chord_placement import ChordPlacement
from apps.songwriter.models.line import Line
from apps.songwriter.models.song import Song
from apps.songwriter.models.song_note import SongNote
from apps.songwriter.models.song_section import SongSection

# Request schemas (Pydantic only)
from apps.songwriter.models.requests import (
    AddChordRequest,
    ChordPlacementRequest,
    LineRequest,
    Section,
    SectionUpdateRequest,
    SongCreateRequest,
    SongNoteCreateRequest,
    SongNoteUpdateRequest,
    SongUpdateRequest,
    StructureSuggestion,
)

__all__ = [
    # SQLModel models (database tables)
    "AgentReview",
    "AudioFile",
    "ChordPlacement",
    "Line",
    "Song",
    "SongNote",
    "SongSection",
    # Request schemas (Pydantic)
    "AddChordRequest",
    "ChordPlacementRequest",
    "LineRequest",
    "Section",
    "SectionUpdateRequest",
    "SongCreateRequest",
    "SongNoteCreateRequest",
    "SongNoteUpdateRequest",
    "SongUpdateRequest",
    "StructureSuggestion",
]
