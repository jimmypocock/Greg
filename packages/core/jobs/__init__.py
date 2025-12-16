"""
Background job management.

Provides infrastructure for tracking long-running tasks
with progress updates and status notifications.

For Redis-backed queue (production):
    - Run worker: uv run arq src.jobs.worker.WorkerSettings
    - Use enqueue_job() to add jobs to queue

For in-memory processing (development):
    - Use process_document_job() directly with asyncio.create_task()
"""

from packages.core.jobs.exceptions import (
    JobAccessDeniedError,
    JobCannotBeCancelledError,
    JobCancellationError,
    JobError,
    JobNotFoundError,
)
from packages.core.jobs.handlers import register_job_exception_handlers
from packages.core.jobs.manager import JobManager, job_manager
from packages.core.jobs.models import JobInfo, JobProgress, JobStatus, JobType
from packages.core.jobs.queue import (
    close_redis_pool,
    enqueue_job,
    get_redis_pool,
    get_redis_settings,
)
from packages.core.jobs.schemas import (
    JobCancelResponse,
    JobDetailResponse,
    JobListResponse,
    JobProgressResponse,
    JobResponse,
)

__all__ = [
    # Exceptions
    "JobAccessDeniedError",
    "JobCannotBeCancelledError",
    "JobCancellationError",
    "JobError",
    "JobNotFoundError",
    # Handlers
    "register_job_exception_handlers",
    # Job manager
    "JobManager",
    "job_manager",
    # Models
    "JobInfo",
    "JobProgress",
    "JobStatus",
    "JobType",
    # Redis queue
    "close_redis_pool",
    "enqueue_job",
    "get_redis_pool",
    "get_redis_settings",
    # Schemas
    "JobCancelResponse",
    "JobDetailResponse",
    "JobListResponse",
    "JobProgressResponse",
    "JobResponse",
]
