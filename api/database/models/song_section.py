"""
SongSection model.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.models.base import Base, TimestampMixin
from api.enums import SectionType

if TYPE_CHECKING:
    from api.database.models.line import Line
    from api.database.models.section_version import SectionVersion
    from api.database.models.song import Song
    from api.database.models.song_note import SongNote


class SongSection(Base, TimestampMixin):
    """A section of a song (verse, chorus, etc.)."""

    __tablename__ = "song_sections"

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

    type: Mapped[SectionType] = mapped_column(
        Enum(SectionType, name="sectiontype", create_type=False),
        nullable=False,
    )
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    song: Mapped["Song"] = relationship("Song", back_populates="sections")
    versions: Mapped[list["SectionVersion"]] = relationship(
        "SectionVersion",
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="SectionVersion.version_number",
    )
    notes_list: Mapped[list["SongNote"]] = relationship(
        "SongNote",
        back_populates="section",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        label = self.type.value
        if self.number:
            label += f" {self.number}"
        return f"<SongSection {label}>"

    @property
    def main_version(self) -> "SectionVersion | None":
        """Get the main version of this section."""
        return next((v for v in self.versions if v.is_main), None)

    @property
    def lines(self) -> list["Line"]:
        """Get lines from the main version (for backward compatibility)."""
        main = self.main_version
        return main.lines if main else []

    def get_lyrics_text(self) -> str:
        """Get all lyrics in this section as a single string (from main version)."""
        return "\n".join(line.text for line in self.lines)
