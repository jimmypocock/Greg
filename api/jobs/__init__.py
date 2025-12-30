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

from api.jobs.exceptions import (
    JobAccessDeniedError,
    JobCannotBeCancelledError,
    JobCancellationError,
    JobError,
    JobNotFoundError,
)
from api.jobs.handlers import register_job_exception_handlers
from api.jobs.manager import JobManager, job_manager
from api.jobs.models import JobInfo, JobProgress, JobStatus, JobType
from api.jobs.queue import (
    close_redis_pool,
    enqueue_job,
    get_redis_pool,
    get_redis_settings,
)
from api.jobs.schemas import (
    JobCancelResponse,
    JobDetailResponse,
    JobListResponse,
    JobProgressResponse,
    JobResponse,
)
from api.jobs.yjs_sync_worker import YjsSyncWorker, yjs_sync_worker

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
    # Yjs sync worker
    "YjsSyncWorker",
    "yjs_sync_worker",
]
