"""Line model (SQLModel - database table for lyric lines)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, DateTime, text as sa_text
from sqlmodel import Field, Relationship, SQLModel

from api.models.utils import utc_now

if TYPE_CHECKING:
    from api.models.chord_placement import ChordPlacement
    from api.models.section_version import SectionVersion


class Line(SQLModel, table=True):
    """A single line of lyrics within a section version."""

    __tablename__ = "lines"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    section_version_id: uuid.UUID = Field(foreign_key="section_versions.id", index=True)

    # Position and content
    order: int = Field(default=0)
    text: str = Field(default="")

    # Notes for this specific line (e.g., "too cliché", "love this metaphor")
    notes: Optional[str] = None

    # Timestamps - must use timezone-aware columns to match utc_now()
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()")),
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=sa_text("now()")),
    )

    # Relationships
    section_version: Optional["SectionVersion"] = Relationship(back_populates="lines")
    chords: list["ChordPlacement"] = Relationship(
        back_populates="line",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "ChordPlacement.position"},
    )
