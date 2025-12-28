"""
YjsDocument model.
"""

import uuid

from sqlalchemy import ForeignKey, LargeBinary, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database.models.base import Base, TimestampMixin


class YjsDocument(Base, TimestampMixin):
    """Persistent storage for Yjs document state."""

    __tablename__ = "yjs_documents"
    __table_args__ = (
        UniqueConstraint("song_id", "document_name", name="uq_yjs_documents_song_doc"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    song_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("songs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Document identifier (e.g., 'main' for the whole song, or 'section-{id}')
    document_name: Mapped[str] = mapped_column(String(100), default="main", nullable=False)

    # Yjs state vector for efficient sync
    state_vector: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    # Full Yjs document state (binary encoded)
    document_state: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)

    # Track who made the last update
    last_updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<YjsDocument '{self.document_name}'>"
