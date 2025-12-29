"""
Line model.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.models.base import Base, TimestampMixin
from api.enums import LineType

if TYPE_CHECKING:
    from api.database.models.chord_placement import ChordPlacement
    from api.database.models.section_version import SectionVersion


class Line(Base, TimestampMixin):
    """A single line in a song document (lyric, chord, section header, or annotation)."""

    __tablename__ = "lines"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    section_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("section_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    line_type: Mapped[LineType] = mapped_column(
        Enum(LineType, name="linetype", create_type=False),
        default=LineType.LYRIC,
        nullable=False,
    )
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        preview = self.text[:30] + "..." if len(self.text) > 30 else self.text
        return f"<Line {self.order}: '{preview}'>"

    # Relationships
    section_version: Mapped["SectionVersion"] = relationship("SectionVersion", back_populates="lines")
    chords: Mapped[list["ChordPlacement"]] = relationship(
        "ChordPlacement",
        back_populates="line",
        cascade="all, delete-orphan",
        order_by="ChordPlacement.position",
    )
