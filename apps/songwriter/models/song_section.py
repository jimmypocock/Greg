"""SongSection model (SQLModel - works for API + DB)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Enum, text
from sqlmodel import Field, Relationship, SQLModel

from apps.songwriter.enums import SectionType

if TYPE_CHECKING:
    from apps.songwriter.models.line import Line
    from apps.songwriter.models.song import Song
    from apps.songwriter.models.song_note import SongNote


class SongSection(SQLModel, table=True):
    """A section of a song (verse, chorus, etc.)."""

    __tablename__ = "song_sections"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    song_id: uuid.UUID = Field(foreign_key="songs.id", index=True)

    type: SectionType = Field(
        sa_column=Column(
            Enum(SectionType, name="sectiontype", create_type=False),
            nullable=False,
        ),
    )
    number: Optional[int] = None  # e.g., Verse 1, Verse 2
    order: int = 0  # Position in song
    notes: Optional[str] = None  # Section-specific notes

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"server_default": text("now()")},
    )

    # Relationships
    song: Optional["Song"] = Relationship(back_populates="sections")
    lines: list["Line"] = Relationship(
        back_populates="section",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "Line.order"},
    )
    notes_list: list["SongNote"] = Relationship(
        back_populates="section",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def get_lyrics_text(self) -> str:
        """Get all lyrics in this section as a single string."""
        return "\n".join(line.text for line in self.lines)
