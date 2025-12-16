"""
Job data models.

Defines the structure for background jobs and their status tracking.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    """Status of a background job."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, Enum):
    """Type of background job."""

    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_PROCESS = "document_process"
    URL_PROCESS = "url_process"


@dataclass
class JobProgress:
    """Progress information for a job."""

    stage: str
    percent: float = 0.0
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobInfo:
    """Information about a background job."""

    job_id: str
    job_type: JobType
    status: JobStatus = JobStatus.PENDING
    progress: JobProgress | None = None
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "job_id": self.job_id,
            "job_type": self.job_type.value,
            "status": self.status.value,
            "progress": {
                "stage": self.progress.stage,
                "percent": self.progress.percent,
                "message": self.progress.message,
                "details": self.progress.details,
            }
            if self.progress
            else None,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
