"""Audio analysis status enum."""

from enum import Enum


class AnalysisStatus(str, Enum):
    """Status of audio file analysis."""

    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
