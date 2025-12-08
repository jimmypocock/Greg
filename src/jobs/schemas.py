"""
Pydantic schemas for job management.

Defines request/response schemas for job endpoints.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from src.jobs.models import JobInfo


# Schemas


class JobCancelResponse(BaseModel):
    """Response when a job is cancelled."""

    job_id: str
    message: str


class JobListResponse(BaseModel):
    """Response containing list of jobs."""

    count: int
    jobs: list["JobResponse"]


class JobProgressResponse(BaseModel):
    """Job progress information."""

    details: dict | None = None
    message: str
    percent: float
    stage: str

    @classmethod
    def from_progress(cls, progress: dict) -> "JobProgressResponse":
        """Create response from progress dict."""
        return cls(
            details=progress.get("details"),
            message=progress.get("message", ""),
            percent=progress.get("percent", 0),
            stage=progress.get("stage", ""),
        )


class JobResponse(BaseModel):
    """Single job response."""

    completed_at: str | None
    created_at: str
    error: str | None
    job_id: str
    job_type: str
    progress: JobProgressResponse | None
    result: dict | None
    started_at: str | None
    status: str

    @classmethod
    def from_model(cls, job: "JobInfo") -> "JobResponse":
        """Create response from JobInfo model."""
        job_dict = job.to_dict()
        return cls(
            completed_at=job_dict["completed_at"],
            created_at=job_dict["created_at"],
            error=job_dict["error"],
            job_id=job_dict["job_id"],
            job_type=job_dict["job_type"],
            progress=JobProgressResponse.from_progress(job_dict["progress"])
            if job_dict["progress"]
            else None,
            result=job_dict["result"],
            started_at=job_dict["started_at"],
            status=job_dict["status"],
        )


class JobDetailResponse(BaseModel):
    """Response containing a single job."""

    job: JobResponse
