"""Audio analysis status enum."""

from enum import Enum


class AnalysisStatus(str, Enum):
    """Status of audio file analysis."""

    PENDING = "PENDING"
    ANALYZING = "ANALYZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
