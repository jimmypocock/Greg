"""
Job management routes.

Provides endpoints for monitoring and controlling background jobs.

Endpoints:
    GET  /jobs              - List all jobs (admin only)
    GET  /jobs/{job_id}     - Get job status
    POST /jobs/{job_id}/cancel - Cancel a job
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Query

from packages.core.auth import AdminUser, CurrentUser
from packages.core.jobs import (
    JobCancelResponse,
    JobCannotBeCancelledError,
    JobCancellationError,
    JobDetailResponse,
    JobListResponse,
    JobNotFoundError,
    JobProgressResponse,
    JobResponse,
    JobStatus,
    JobType,
    job_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# Routes


@router.post("/{job_id}/cancel", response_model=JobCancelResponse)
async def cancel_job(job_id: str, user: CurrentUser):
    """Cancel a pending or running job. Cancellation is best-effort."""
    job = await job_manager.get_job(job_id)

    if not job:
        raise JobNotFoundError(job_id)

    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        raise JobCannotBeCancelledError(job.status.value)

    success = await job_manager.cancel_job(job_id)

    if not success:
        raise JobCancellationError()

    return JobCancelResponse(job_id=job_id, message="Job cancelled")


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(job_id: str, user: CurrentUser):
    """Get the status and details of a specific job."""
    job = await job_manager.get_job(job_id)

    if not job:
        raise JobNotFoundError(job_id)

    return JobDetailResponse(job=JobResponse.from_model(job))


@router.get("", response_model=JobListResponse)
async def list_jobs(
    admin: AdminUser,
    status_filter: Annotated[
        JobStatus | None,
        Query(alias="status", description="Filter by job status"),
    ] = None,
    job_type: Annotated[
        JobType | None,
        Query(description="Filter by job type"),
    ] = None,
    limit: Annotated[
        int,
        Query(ge=1, le=100, description="Maximum jobs to return"),
    ] = 50,
):
    """List all jobs with optional filtering. Admin only."""
    jobs = await job_manager.list_jobs(
        status=status_filter,
        job_type=job_type,
        limit=limit,
    )

    return JobListResponse(
        count=len(jobs),
        jobs=[JobResponse.from_model(job) for job in jobs],
    )
