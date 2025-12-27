"""SectionVersion model (SQLModel - works for API + DB)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import text
from sqlmodel import Field, Relationship, SQLModel

from api.models.utils import utc_now

if TYPE_CHECKING:
    from api.models.audio_file import AudioFile
    from api.models.line import Line
    from api.models.song_section import SongSection


class SectionVersion(SQLModel, table=True):
    """A version of a song section for workshopping different takes."""

    __tablename__ = "section_versions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    section_id: uuid.UUID = Field(foreign_key="song_sections.id", index=True)

    # Version info
    version_number: int = Field(default=1)
    name: Optional[str] = Field(default=None, max_length=100)
    is_main: bool = Field(default=False)

    # Optional notes for this version
    notes: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": text("now()")},
    )
    updated_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": text("now()")},
    )

    # Relationships
    section: Optional["SongSection"] = Relationship(back_populates="versions")
    lines: list["Line"] = Relationship(
        back_populates="section_version",
        sa_relationship_kwargs={"cascade": "all, delete-orphan", "order_by": "Line.order"},
    )
    audio_files: list["AudioFile"] = Relationship(
        back_populates="section_version",
        sa_relationship_kwargs={"cascade": "save-update, merge"},
    )

    def get_lyrics_text(self) -> str:
        """Get all lyrics in this version as a single string."""
        return "\n".join(line.text for line in self.lines)
