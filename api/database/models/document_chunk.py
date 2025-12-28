"""
Document Chunk model for text chunks with vector embeddings.

Uses pgvector for similarity search with support for multiple embedding providers.
"""

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.models.base import Base

if TYPE_CHECKING:
    from api.database.models.document import Document

# Embedding dimensions by provider
LOCAL_EMBEDDING_DIM = 384   # all-MiniLM-L6-v2
OPENAI_EMBEDDING_DIM = 1536  # text-embedding-3-small, ada-002


class EmbeddingProvider(str, enum.Enum):
    """Supported embedding providers."""
    LOCAL = "local"
    OPENAI = "openai"


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

    # Dual embedding columns - one will be populated based on provider
    embedding_local = mapped_column(
        Vector(LOCAL_EMBEDDING_DIM),
        nullable=True,
    )
    embedding_openai = mapped_column(
        Vector(OPENAI_EMBEDDING_DIM),
        nullable=True,
    )

    # Track which embedding provider was used
    embedding_provider: Mapped[EmbeddingProvider] = mapped_column(
        Enum(
            EmbeddingProvider,
            name="embedding_provider_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],  # Use .value not .name
        ),
        nullable=False,
        default=EmbeddingProvider.LOCAL,
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

    def __repr__(self) -> str:
        preview = self.content[:25] + "..." if len(self.content) > 25 else self.content
        return f"<DocumentChunk #{self.chunk_index} '{preview}'>"

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
    )

    @property
    def embedding(self) -> Optional[list[float]]:
        """Get the active embedding based on provider."""
        if self.embedding_provider == EmbeddingProvider.LOCAL:
            return self.embedding_local
        elif self.embedding_provider == EmbeddingProvider.OPENAI:
            return self.embedding_openai
        return None

    def set_embedding(self, embedding: list[float], provider: EmbeddingProvider) -> None:
        """Set the embedding for the specified provider."""
        self.embedding_provider = provider
        if provider == EmbeddingProvider.LOCAL:
            self.embedding_local = embedding
            self.embedding_openai = None
        elif provider == EmbeddingProvider.OPENAI:
            self.embedding_openai = embedding
            self.embedding_local = None

    @staticmethod
    def get_embedding_column(provider: EmbeddingProvider):
        """Get the SQLAlchemy column for the specified provider (for queries)."""
        if provider == EmbeddingProvider.LOCAL:
            return DocumentChunk.embedding_local
        elif provider == EmbeddingProvider.OPENAI:
            return DocumentChunk.embedding_openai
        raise ValueError(f"Unknown embedding provider: {provider}")
