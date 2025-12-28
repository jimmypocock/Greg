"""
SongNote model.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.models.base import Base, TimestampMixin
from api.enums import NoteType

if TYPE_CHECKING:
    from api.database.models.song import Song
    from api.database.models.song_section import SongSection


class SongNote(Base, TimestampMixin):
    """A note, idea, or piece of context attached to a song."""

    __tablename__ = "song_notes"

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
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("song_sections.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    note_type: Mapped[NoteType] = mapped_column(
        Enum(NoteType, name="notetype", create_type=False),
        default=NoteType.IDEA,
        nullable=False,
    )

    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        preview = self.content[:25] + "..." if len(self.content) > 25 else self.content
        resolved = " ✓" if self.is_resolved else ""
        return f"<SongNote [{self.note_type.value}] '{preview}'{resolved}>"

    # Relationships
    song: Mapped["Song"] = relationship("Song", back_populates="song_notes")
    section: Mapped["SongSection | None"] = relationship("SongSection", back_populates="notes_list")
