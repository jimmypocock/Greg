"""
ChordPlacement model.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from api.database.models.line import Line


class ChordPlacement(Base, TimestampMixin):
    """A chord placed at a specific position in a lyric line."""

    __tablename__ = "chord_placements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    line_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chord: Mapped[str] = mapped_column(String(20), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    def __repr__(self) -> str:
        return f"<ChordPlacement {self.chord} @{self.position}>"

    # Relationships
    line: Mapped["Line"] = relationship("Line", back_populates="chords")
