"""
Background job management.

Provides infrastructure for tracking long-running tasks
with progress updates and status notifications.

For Redis-backed queue (production):
    - Run worker: uv run arq src.jobs.worker.WorkerSettings
    - Use enqueue_job() to add jobs to queue

For in-memory processing (development):
    - Use process_document_async() directly with asyncio.create_task()
"""

from src.jobs.manager import JobManager, job_manager
from src.jobs.models import JobInfo, JobProgress, JobStatus, JobType
from src.jobs.document_worker import process_document_async, process_url_async
from src.jobs.queue import (
    enqueue_job,
    get_redis_pool,
    close_redis_pool,
    get_redis_settings,
)

__all__ = [
    # Job manager
    "JobManager",
    "job_manager",
    # Models
    "JobInfo",
    "JobProgress",
    "JobStatus",
    "JobType",
    # In-memory processing
    "process_document_async",
    "process_url_async",
    # Redis queue
    "enqueue_job",
    "get_redis_pool",
    "close_redis_pool",
    "get_redis_settings",
]
