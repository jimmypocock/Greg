"""YjsDocument model for persisting Yjs CRDT state."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import LargeBinary, UniqueConstraint, text
from sqlmodel import Column, Field, SQLModel

from apps.songwriter.models.utils import utc_now


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
        sa_column=Column(LargeBinary, nullable=True),
    )

    # Full Yjs document state (binary encoded)
    document_state: Optional[bytes] = Field(
        default=None,
        sa_column=Column(LargeBinary, nullable=True),
    )

    # Track who made the last update
    last_updated_by: Optional[uuid.UUID] = Field(default=None, foreign_key="users.id")

    # Timestamps
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": text("now()")},
    )
