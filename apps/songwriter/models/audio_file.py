"""AudioFile model (SQLModel - works for API + DB)."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Column, Enum, text
from sqlmodel import Field, Relationship, SQLModel

from apps.songwriter.enums import AnalysisStatus

if TYPE_CHECKING:
    from apps.songwriter.models.section_version import SectionVersion


class AudioFile(SQLModel, table=True):
    """An uploaded audio file for a song with analysis results."""

    __tablename__ = "audio_files"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    song_id: uuid.UUID = Field(foreign_key="songs.id", index=True)

    # Optional link to a specific section version (NULL = song-level audio)
    section_version_id: Optional[uuid.UUID] = Field(
        default=None, foreign_key="section_versions.id", index=True
    )

    # File info
    filename: str = Field(max_length=255)  # Original filename
    display_name: Optional[str] = Field(default=None, max_length=255)  # User-editable name
    storage_path: str = Field(max_length=500)
    mime_type: str = Field(max_length=100)
    file_size_bytes: int

    # Audio metadata
    duration_seconds: Optional[float] = None

    # Analysis results
    detected_tempo: Optional[float] = None
    detected_key: Optional[str] = Field(default=None, max_length=20)
    detected_time_signature: Optional[str] = Field(default=None, max_length=10)
    confidence_tempo: Optional[float] = None
    confidence_key: Optional[float] = None
    confidence_time_signature: Optional[float] = None

    # Chord progression as JSON: [{"start": 0.0, "end": 2.5, "chord": "C"}, ...]
    detected_chords: Optional[str] = None

    # Beat positions as JSON: [0.5, 1.0, 1.5, 2.0, ...]
    beat_positions: Optional[str] = None

    # Analysis status
    analysis_status: AnalysisStatus = Field(
        default=AnalysisStatus.PENDING,
        sa_column=Column(
            Enum(AnalysisStatus, name="analysisstatus", create_type=False),
            nullable=False,
            server_default="PENDING",
        ),
    )
    analysis_error: Optional[str] = None

    # If true, auto-apply detected values to song metadata
    is_reference: bool = Field(default=False)

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
    section_version: Optional["SectionVersion"] = Relationship(back_populates="audio_files")
