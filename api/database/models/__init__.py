"""
Database models.

One model per file for clean organization.
"""

from api.database.models.base import Base, TimestampMixin
from api.database.models.user import User, UserRole, UserPlan, PLAN_CREDITS
from api.database.models.invite import Invite, InviteType
from api.database.models.api_key import APIKey
from api.database.models.ai_request import AIRequest, LLMProvider, RequestType
from api.database.models.document import Document, DocumentStatus
from api.database.models.document_chunk import DocumentChunk, EmbeddingProvider
from api.database.models.refresh_token import RefreshToken

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
]
