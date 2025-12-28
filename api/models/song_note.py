"""SongNote model (SQLModel - database table for brain dump notes)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, Enum, text
from sqlmodel import Field, Relationship, SQLModel

from api.enums import NoteType
from api.models.utils import utc_now

if TYPE_CHECKING:
    from api.models.song import Song
    from api.models.song_section import SongSection


class SongNote(SQLModel, table=True):
    """A note, idea, or piece of context attached to a song."""

    __tablename__ = "song_notes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # Foreign keys
    song_id: uuid.UUID = Field(foreign_key="songs.id", index=True)
    section_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="song_sections.id", index=True
    )

    # Note categorization
    note_type: NoteType = Field(
        default=NoteType.IDEA,
        sa_column=Column(
            Enum(NoteType, name="notetype", create_type=False),
            nullable=False,
            server_default="IDEA",
        ),
    )

    # Content
    title: Optional[str] = Field(default=None, max_length=200)
    content: str

    # Status (useful for TODOs)
    is_resolved: bool = Field(default=False)

    # Timestamps - must use timezone-aware columns to match utc_now()
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )

    # Relationships
    song: Optional["Song"] = Relationship(back_populates="song_notes")
    section: Optional["SongSection"] = Relationship(back_populates="notes_list")
