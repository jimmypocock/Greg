"""
Job management routes.

Endpoints:
    GET  /jobs           - List all jobs (admin only)
    GET  /jobs/{job_id}  - Get job status
    POST /jobs/{job_id}/cancel - Cancel a job
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from src.auth import CurrentUser, AdminUser
from src.database import User
from src.jobs import job_manager, JobStatus, JobType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("")
async def list_jobs(
    admin: AdminUser,
    status: Optional[JobStatus] = Query(None, description="Filter by job status"),
    job_type: Optional[JobType] = Query(None, description="Filter by job type"),
    limit: int = Query(50, ge=1, le=100, description="Maximum jobs to return"),
):
    """
    List all jobs with optional filtering. Admin only.

    Returns jobs sorted by creation time (newest first).
    """
    jobs = await job_manager.list_jobs(
        status=status,
        job_type=job_type,
        limit=limit,
    )

    return {
        "jobs": [job.to_dict() for job in jobs],
        "count": len(jobs),
    }


@router.get("/{job_id}")
async def get_job(job_id: str, user: CurrentUser):
    """
    Get the status and details of a specific job.

    Returns current progress, result (if completed), or error (if failed).
    """
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return {"job": job.to_dict()}


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str, user: CurrentUser):
    """
    Cancel a pending or running job.

    Note: Cancellation is best-effort. Jobs may complete before
    cancellation takes effect.
    """
    job = await job_manager.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status.value}",
        )

    success = await job_manager.cancel_job(job_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to cancel job")

    return {"message": "Job cancelled", "job_id": job_id}
