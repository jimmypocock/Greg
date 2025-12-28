"""Songwriter models."""

# IMPORTANT: Import User model first to ensure it's registered before Song
# models that have foreign keys to users.id are loaded
from api.database.models import User  # noqa: F401

# SQLModel models (API + DB)
from api.models.agent_review import AgentReview
from api.models.audio_file import AudioFile
from api.models.chat_message import ChatMessage
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
    "ChatMessage",
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
