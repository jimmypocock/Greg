"""
Database models.

One model per file for clean organization.
"""

from src.database.models.base import Base, TimestampMixin
from src.database.models.user import User, UserRole
from src.database.models.invite import Invite
from src.database.models.api_key import APIKey
from src.database.models.ai_request import AIRequest, LLMProvider, RequestType
from src.database.models.document import Document, DocumentStatus
from src.database.models.document_chunk import DocumentChunk

__all__ = [
    # Base
    "Base",
    "TimestampMixin",
    # User
    "User",
    "UserRole",
    # Invite
    "Invite",
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
]
