"""Songwriter models."""

# SQLModel models (API + DB)
from api.models.agent_review import AgentReview
from api.models.audio_file import AudioFile
from api.models.chord_placement import ChordPlacement
from api.models.line import Line
from api.models.section_version import SectionVersion
from api.models.song import Song
from api.models.song_collaborator import SongCollaborator
from api.models.song_note import SongNote
from api.models.song_section import SongSection
from api.models.song_share_link import SongShareLink
from api.models.yjs_document import YjsDocument

# Request schemas (Pydantic only)
from api.models.requests import (
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
    "SectionVersion",
    "Song",
    "SongCollaborator",
    "SongNote",
    "SongSection",
    "SongShareLink",
    "YjsDocument",
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
