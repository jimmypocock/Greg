"""
ARQ worker for background job processing.

Run with: uv run arq src.jobs.worker.WorkerSettings
"""

import logging
import uuid
from pathlib import Path
from typing import Any

from arq import cron
from arq.connections import RedisSettings

from src.jobs.queue import get_redis_settings
from src.jobs.manager import job_manager

logger = logging.getLogger(__name__)


async def process_document_arq(
    ctx: dict[str, Any],
    job_id: str,
    document_id: str,
    file_path: str,
    chunk_size: int,
) -> dict[str, Any]:
    """
    Process a document upload job via ARQ worker.

    This is called by the ARQ worker when a document upload is queued.
    """
    from src.jobs.document_worker import process_document_job

    logger.info(f"Worker processing document job {job_id}")

    try:
        result = await process_document_job(
            job_id=job_id,
            document_id=uuid.UUID(document_id),
            file_path=Path(file_path),
            chunk_size=chunk_size,
        )
        return result

    except Exception as e:
        logger.error(f"Worker failed on job {job_id}: {e}")
        await job_manager.fail_job(job_id, str(e))
        raise


async def process_url_arq(
    ctx: dict[str, Any],
    job_id: str,
    document_id: str,
    url: str,
    chunk_size: int,
) -> dict[str, Any]:
    """
    Process a URL processing job via ARQ worker.

    This is called by the ARQ worker when a URL processing is queued.
    """
    from src.jobs.document_worker import process_url_job

    logger.info(f"Worker processing URL job {job_id}: {url}")

    try:
        result = await process_url_job(
            job_id=job_id,
            document_id=uuid.UUID(document_id),
            url=url,
            chunk_size=chunk_size,
        )
        return result

    except Exception as e:
        logger.error(f"Worker failed on job {job_id}: {e}")
        await job_manager.fail_job(job_id, str(e))
        raise


async def cleanup_old_jobs(ctx: dict[str, Any]) -> int:
    """
    Periodic task to clean up old completed jobs.

    Runs every hour to remove jobs older than 24 hours.
    """
    removed = await job_manager.cleanup_old_jobs(max_age_hours=24)
    if removed > 0:
        logger.info(f"Cleaned up {removed} old jobs")
    return removed


async def startup(ctx: dict[str, Any]) -> None:
    """Worker startup hook."""
    logger.info("ARQ worker starting up")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Worker shutdown hook."""
    logger.info("ARQ worker shutting down")


class WorkerSettings:
    """ARQ worker settings."""

    # Redis connection
    redis_settings: RedisSettings = get_redis_settings()

    # Job functions
    functions = [
        process_document_arq,
        process_url_arq,
    ]

    # Cron jobs
    cron_jobs = [
        cron(cleanup_old_jobs, hour={0, 6, 12, 18}, minute=0),  # Every 6 hours
    ]

    # Lifecycle hooks
    on_startup = startup
    on_shutdown = shutdown

    # Worker settings
    max_jobs = 10
    job_timeout = 600  # 10 minutes
    keep_result = 3600  # 1 hour
    retry_jobs = True
    max_tries = 3
