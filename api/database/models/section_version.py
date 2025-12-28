"""
SectionVersion model.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from api.database.models.audio_file import AudioFile
    from api.database.models.line import Line
    from api.database.models.song_section import SongSection


class SectionVersion(Base, TimestampMixin):
    """A version of a song section for workshopping different takes."""

    __tablename__ = "section_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("song_sections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    version_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_main: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    section: Mapped["SongSection"] = relationship("SongSection", back_populates="versions")
    lines: Mapped[list["Line"]] = relationship(
        "Line",
        back_populates="section_version",
        cascade="all, delete-orphan",
        order_by="Line.order",
    )
    audio_files: Mapped[list["AudioFile"]] = relationship(
        "AudioFile",
        back_populates="section_version",
    )

    def __repr__(self) -> str:
        name = self.name or f"v{self.version_number}"
        main = " (main)" if self.is_main else ""
        return f"<SectionVersion {name}{main}>"

    def get_lyrics_text(self) -> str:
        """Get all lyrics in this version as a single string."""
        return "\n".join(line.text for line in self.lines)
