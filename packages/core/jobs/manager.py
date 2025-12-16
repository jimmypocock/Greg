"""
Job manager for background task tracking.

Provides a centralized way to create, update, and monitor background jobs.
Uses an in-memory store suitable for single-instance deployments.
"""

import asyncio
import logging
import uuid as uuid_lib
from datetime import datetime
from typing import Any, Callable, Coroutine
from uuid import UUID

from packages.core.jobs.models import JobInfo, JobProgress, JobStatus, JobType

logger = logging.getLogger(__name__)


class JobManager:
    """
    Manages background jobs and their lifecycle.

    Thread-safe job tracking with support for progress updates
    and WebSocket notifications.
    """

    def __init__(self):
        self._jobs: dict[str, JobInfo] = {}
        self._subscribers: dict[str, list[Callable[[JobInfo], Coroutine]]] = {}
        self._lock = asyncio.Lock()

    async def create_job(self, job_type: JobType, user_id: UUID) -> JobInfo:
        """
        Create a new job and return its info.

        Args:
            job_type: The type of job being created.
            user_id: The ID of the user creating the job.

        Returns:
            JobInfo with a unique job_id.
        """
        job_id = str(uuid_lib.uuid4())
        job = JobInfo(job_id=job_id, job_type=job_type, user_id=user_id)

        async with self._lock:
            self._jobs[job_id] = job

        logger.info(f"Created job {job_id} of type {job_type.value} for user {user_id}")
        return job

    async def get_job(self, job_id: str) -> JobInfo | None:
        """Get job info by ID."""
        async with self._lock:
            return self._jobs.get(job_id)

    async def update_progress(
        self,
        job_id: str,
        stage: str,
        percent: float = 0.0,
        message: str = "",
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        Update job progress and notify subscribers.

        Args:
            job_id: The job to update.
            stage: Current processing stage.
            percent: Completion percentage (0-100).
            message: Human-readable status message.
            details: Additional details about the progress.
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                logger.warning(f"Attempted to update non-existent job {job_id}")
                return

            job.progress = JobProgress(
                stage=stage,
                percent=percent,
                message=message,
                details=details or {},
            )

            if job.status == JobStatus.PENDING:
                job.status = JobStatus.RUNNING
                job.started_at = datetime.utcnow()

        await self._notify_subscribers(job_id)
        logger.debug(f"Job {job_id}: {stage} ({percent:.1f}%) - {message}")

    async def complete_job(self, job_id: str, result: dict[str, Any]) -> None:
        """
        Mark a job as completed with its result.

        Args:
            job_id: The job to complete.
            result: The job's output data.
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return

            job.status = JobStatus.COMPLETED
            job.result = result
            job.completed_at = datetime.utcnow()
            job.progress = JobProgress(
                stage="completed",
                percent=100.0,
                message="Processing complete",
            )

        await self._notify_subscribers(job_id)
        logger.info(f"Job {job_id} completed successfully")

    async def fail_job(self, job_id: str, error: str) -> None:
        """
        Mark a job as failed with an error message.

        Args:
            job_id: The job that failed.
            error: Description of the failure.
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return

            job.status = JobStatus.FAILED
            job.error = error
            job.completed_at = datetime.utcnow()

        await self._notify_subscribers(job_id)
        logger.error(f"Job {job_id} failed: {error}")

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a pending or running job.

        Args:
            job_id: The job to cancel.

        Returns:
            True if cancelled, False if job not found or already complete.
        """
        async with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return False

            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED):
                return False

            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.utcnow()

        await self._notify_subscribers(job_id)
        logger.info(f"Job {job_id} cancelled")
        return True

    async def subscribe(
        self, job_id: str, callback: Callable[[JobInfo], Coroutine]
    ) -> None:
        """
        Subscribe to updates for a specific job.

        Args:
            job_id: The job to subscribe to.
            callback: Async function called with JobInfo on updates.
        """
        async with self._lock:
            if job_id not in self._subscribers:
                self._subscribers[job_id] = []
            self._subscribers[job_id].append(callback)

    async def unsubscribe(
        self, job_id: str, callback: Callable[[JobInfo], Coroutine]
    ) -> None:
        """
        Unsubscribe from job updates.

        Args:
            job_id: The job to unsubscribe from.
            callback: The callback to remove.
        """
        async with self._lock:
            if job_id in self._subscribers:
                try:
                    self._subscribers[job_id].remove(callback)
                except ValueError:
                    pass

    async def _notify_subscribers(self, job_id: str) -> None:
        """Notify all subscribers of a job update."""
        async with self._lock:
            job = self._jobs.get(job_id)
            subscribers = self._subscribers.get(job_id, []).copy()

        if not job or not subscribers:
            return

        for callback in subscribers:
            try:
                await callback(job)
            except Exception as e:
                logger.error(f"Error notifying subscriber for job {job_id}: {e}")

    async def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """
        Remove completed jobs older than max_age_hours.

        Args:
            max_age_hours: Maximum age of completed jobs to keep.

        Returns:
            Number of jobs removed.
        """
        cutoff = datetime.utcnow()
        removed = 0

        async with self._lock:
            to_remove = []
            for job_id, job in self._jobs.items():
                if job.completed_at:
                    age = (cutoff - job.completed_at).total_seconds() / 3600
                    if age > max_age_hours:
                        to_remove.append(job_id)

            for job_id in to_remove:
                del self._jobs[job_id]
                self._subscribers.pop(job_id, None)
                removed += 1

        if removed:
            logger.info(f"Cleaned up {removed} old jobs")
        return removed

    async def list_jobs(
        self,
        status: JobStatus | None = None,
        job_type: JobType | None = None,
        user_id: UUID | None = None,
        limit: int = 50,
    ) -> list[JobInfo]:
        """
        List jobs with optional filtering.

        Args:
            status: Filter by job status.
            job_type: Filter by job type.
            user_id: Filter by user who created the job.
            limit: Maximum number of jobs to return.

        Returns:
            List of matching jobs, newest first.
        """
        async with self._lock:
            jobs = list(self._jobs.values())

        if status:
            jobs = [j for j in jobs if j.status == status]
        if job_type:
            jobs = [j for j in jobs if j.job_type == job_type]
        if user_id:
            jobs = [j for j in jobs if j.user_id == user_id]

        jobs.sort(key=lambda j: j.created_at, reverse=True)
        return jobs[:limit]


# Global job manager instance
job_manager = JobManager()
