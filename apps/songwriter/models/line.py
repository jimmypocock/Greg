"""Line model (SQLModel - database table for lyric lines)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import text as sa_text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from apps.songwriter.models.chord_placement import ChordPlacement
    from apps.songwriter.models.song_section import SongSection


class Line(SQLModel, table=True):
    """A single line of lyrics within a song section."""

    __tablename__ = "lines"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    section_id: uuid.UUID = Field(foreign_key="song_sections.id", index=True)

    # Position and content
    order: int = Field(default=0)
    text: str = Field(default="")

    # Notes for this specific line (e.g., "too cliché", "love this metaphor")
    notes: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"server_default": sa_text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column_kwargs={"server_default": sa_text("now()")},
    )

    # Relationships
    section: Optional["SongSection"] = Relationship(back_populates="lines")
    chords: list["ChordPlacement"] = Relationship(
        back_populates="line",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "ChordPlacement.position"},
    )
