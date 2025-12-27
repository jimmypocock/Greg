"""
Job management routes.

Provides endpoints for monitoring and controlling background jobs.

Endpoints:
    GET  /jobs              - List all jobs (admin only)
    GET  /jobs/{job_id}     - Get job status (owner or admin)
    POST /jobs/{job_id}/cancel - Cancel a job (owner or admin)
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Query

from api.auth import AdminUser, CurrentUser
from api.database import UserRole
from api.jobs import (
    JobAccessDeniedError,
    JobCancelResponse,
    JobCannotBeCancelledError,
    JobCancellationError,
    JobDetailResponse,
    JobListResponse,
    JobNotFoundError,
    JobResponse,
    JobStatus,
    JobType,
    job_manager,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# Private functions


def _check_job_access(job, user) -> None:
    """
    Verify user has access to a job.

    Raises:
        JobAccessDeniedError: If user doesn't own the job and isn't admin.
    """
    if job.user_id != user.id and user.role != UserRole.ADMIN:
        raise JobAccessDeniedError(job.job_id)


# Routes


@router.post("/{job_id}/cancel", response_model=JobCancelResponse)
async def cancel_job(job_id: str, user: CurrentUser):
    """Cancel a pending or running job. Only job owner or admin can cancel."""
    job = await job_manager.get_job(job_id)

    if not job:
        raise JobNotFoundError(job_id)

    _check_job_access(job, user)

    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        raise JobCannotBeCancelledError(job.status.value)

    success = await job_manager.cancel_job(job_id)

    if not success:
        raise JobCancellationError()

    logger.info(f"User {user.email} cancelled job {job_id}")

    return JobCancelResponse(job_id=job_id, message="Job cancelled")


@router.get("/{job_id}", response_model=JobDetailResponse)
async def get_job(job_id: str, user: CurrentUser):
    """Get the status and details of a specific job. Only job owner or admin can view."""
    job = await job_manager.get_job(job_id)

    if not job:
        raise JobNotFoundError(job_id)

    _check_job_access(job, user)

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
