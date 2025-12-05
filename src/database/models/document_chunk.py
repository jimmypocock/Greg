"""
Document Chunk model for text chunks with vector embeddings.

Uses pgvector for similarity search.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base

if TYPE_CHECKING:
    from src.database.models.document import Document

# Embedding dimension - matches OpenAI text-embedding-ada-002 / text-embedding-3-small
EMBEDDING_DIMENSION = 1536


class DocumentChunk(Base):
    """Text chunk with vector embedding for similarity search."""

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Chunk position
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    # Content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    token_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    # Vector embedding - pgvector type for similarity search
    embedding = mapped_column(
        Vector(EMBEDDING_DIMENSION),
        nullable=True,
    )

    # Chunk metadata (page number, section headers, etc.)
    chunk_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )

    # Timestamp (no updated_at - chunks are regenerated on reprocess)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
    )
