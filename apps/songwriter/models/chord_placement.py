"""ChordPlacement model (SQLModel - database table for chord positions)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import text
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from apps.songwriter.models.line import Line


class ChordPlacement(SQLModel, table=True):
    """A chord placed at a specific position in a lyric line."""

    __tablename__ = "chord_placements"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    line_id: uuid.UUID = Field(foreign_key="lines.id", index=True)

    # Chord data
    chord: str = Field(max_length=20)  # e.g., "G", "Cmaj7", "F#m"
    position: int = Field(ge=0)  # Character index where chord lands

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
    line: Optional["Line"] = Relationship(back_populates="chords")
