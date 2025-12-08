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

from src.jobs.exceptions import (
    JobCannotBeCancelledError,
    JobCancellationError,
    JobError,
    JobNotFoundError,
)
from src.jobs.handlers import register_job_exception_handlers
from src.jobs.manager import JobManager, job_manager
from src.jobs.models import JobInfo, JobProgress, JobStatus, JobType
from src.jobs.queue import (
    close_redis_pool,
    enqueue_job,
    get_redis_pool,
    get_redis_settings,
)
from src.jobs.schemas import (
    JobCancelResponse,
    JobDetailResponse,
    JobListResponse,
    JobProgressResponse,
    JobResponse,
)

# Import after manager to avoid circular import
from src.jobs.document_worker import process_document_job, process_url_job

__all__ = [
    # Document processing
    "process_document_job",
    "process_url_job",
    # Exceptions
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
