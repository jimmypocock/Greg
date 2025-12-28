"""
AudioFile model.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.models.base import Base, TimestampMixin
from api.enums import AnalysisStatus

if TYPE_CHECKING:
    from api.database.models.section_version import SectionVersion
    from api.database.models.song import Song


class AudioFile(Base, TimestampMixin):
    """An uploaded audio file for a song with analysis results."""

    __tablename__ = "audio_files"

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
    section_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("section_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # File info
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    storage_path: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Audio metadata
    duration_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Analysis results
    detected_tempo: Mapped[float | None] = mapped_column(Float, nullable=True)
    detected_key: Mapped[str | None] = mapped_column(String(20), nullable=True)
    detected_time_signature: Mapped[str | None] = mapped_column(String(10), nullable=True)
    confidence_tempo: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_key: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_time_signature: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Chord progression as JSON: [{"start": 0.0, "end": 2.5, "chord": "C"}, ...]
    detected_chords: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Beat positions as JSON: [0.5, 1.0, 1.5, 2.0, ...]
    beat_positions: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Analysis status
    analysis_status: Mapped[AnalysisStatus] = mapped_column(
        Enum(AnalysisStatus, name="analysisstatus", create_type=False),
        default=AnalysisStatus.PENDING,
        nullable=False,
    )
    analysis_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # If true, auto-apply detected values to song metadata
    is_reference: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    def __repr__(self) -> str:
        name = self.display_name or self.filename
        return f"<AudioFile '{name}' ({self.analysis_status.value})>"

    # Relationships
    song: Mapped["Song"] = relationship("Song", back_populates="audio_files")
    section_version: Mapped["SectionVersion | None"] = relationship(
        "SectionVersion", back_populates="audio_files"
    )
