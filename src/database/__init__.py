"""
Database module.

Provides SQLAlchemy models and async database connection management.
"""

from src.database.connection import (
    close_database,
    get_session,
    get_session_dependency,
    init_database,
)
from src.database.models import (
    AIRequest,
    APIKey,
    Base,
    Document,
    DocumentChunk,
    DocumentStatus,
    Invite,
    LLMProvider,
    RequestType,
    TimestampMixin,
    User,
    UserRole,
)

__all__ = [
    # Connection
    "init_database",
    "close_database",
    "get_session",
    "get_session_dependency",
    # Models
    "Base",
    "TimestampMixin",
    "User",
    "UserRole",
    "Invite",
    "APIKey",
    "AIRequest",
    "LLMProvider",
    "RequestType",
    "Document",
    "DocumentStatus",
    "DocumentChunk",
]
