"""
Database models.

One model per file for clean organization.
"""

from api.database.models.base import Base, TimestampMixin

# Core models
from api.database.models.user import PLAN_CREDITS, User, UserPlan, UserRole
from api.database.models.invite import Invite, InviteType
from api.database.models.api_key import APIKey
from api.database.models.ai_request import AIRequest, LLMProvider, RequestType
from api.database.models.document import Document, DocumentStatus
from api.database.models.document_chunk import DocumentChunk, EmbeddingProvider
from api.database.models.refresh_token import RefreshToken

# Song models
from api.database.models.song import Song
from api.database.models.song_section import SongSection
from api.database.models.section_version import SectionVersion
from api.database.models.line import Line
from api.database.models.chord_placement import ChordPlacement
from api.database.models.song_note import SongNote
from api.database.models.audio_file import AudioFile
from api.database.models.agent_review import AgentReview
from api.database.models.chat_message import ChatMessage
from api.database.models.song_collaborator import SongCollaborator
from api.database.models.song_share_link import SongShareLink
from api.database.models.yjs_document import YjsDocument

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    # User
    "User",
    "UserRole",
    "UserPlan",
    "PLAN_CREDITS",
    # Invite
    "Invite",
    "InviteType",
    # API Key
    "APIKey",
    # AI Request
    "AIRequest",
    "LLMProvider",
    "RequestType",
    # Document
    "Document",
    "DocumentStatus",
    # Document Chunk
    "DocumentChunk",
    "EmbeddingProvider",
    # Refresh Token
    "RefreshToken",
    # Song
    "Song",
    "SongSection",
    "SectionVersion",
    "Line",
    "ChordPlacement",
    "SongNote",
    "AudioFile",
    "AgentReview",
    "ChatMessage",
    "SongCollaborator",
    "SongShareLink",
    "YjsDocument",
]
