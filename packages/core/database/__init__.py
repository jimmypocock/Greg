"""
Database module.

Provides SQLAlchemy models and async database connection management.
"""

from packages.core.database.connection import (
    close_database,
    get_session,
    get_session_dependency,
    init_database,
)
from packages.core.database.models import (
    AIRequest,
    APIKey,
    Base,
    Document,
    DocumentChunk,
    DocumentStatus,
    Invite,
    LLMProvider,
    RefreshToken,
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
    "RefreshToken",
]
