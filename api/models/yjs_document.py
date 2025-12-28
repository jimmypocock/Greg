"""YjsDocument model for persisting Yjs CRDT state."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, LargeBinary, UniqueConstraint, text
from sqlalchemy import Column as SAColumn
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlmodel import Field, SQLModel

from api.models.utils import utc_now


class YjsDocument(SQLModel, table=True):
    """Persistent storage for Yjs document state."""

    __tablename__ = "yjs_documents"
    __table_args__ = (
        UniqueConstraint("song_id", "document_name", name="uq_yjs_documents_song_doc"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    song_id: uuid.UUID = Field(foreign_key="songs.id", index=True)

    # Document identifier (e.g., 'main' for the whole song, or 'section-{id}')
    document_name: str = Field(max_length=100, default="main")

    # Yjs state vector for efficient sync
    state_vector: Optional[bytes] = Field(
        default=None,
        sa_column=SAColumn(LargeBinary, nullable=True),
    )

    # Full Yjs document state (binary encoded)
    document_state: Optional[bytes] = Field(
        default=None,
        sa_column=SAColumn(LargeBinary, nullable=True),
    )

    # Track who made the last update
    # Foreign key constraint defined in database migration
    last_updated_by: Optional[uuid.UUID] = Field(
        default=None,
        sa_column=SAColumn(PGUUID(as_uuid=True), nullable=True),
    )

    # Timestamps - must use timezone-aware columns to match utc_now()
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=SAColumn(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=SAColumn(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
