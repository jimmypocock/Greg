"""
ARQ worker for background job processing.

Run with: uv run arq src.jobs.worker.WorkerSettings
"""

import logging
from typing import Any

from arq import cron
from arq.connections import RedisSettings

from src.jobs.queue import get_redis_settings
from src.jobs.manager import job_manager
from src.jobs.models import JobType

logger = logging.getLogger(__name__)


async def process_document_job(
    ctx: dict[str, Any],
    job_id: str,
    file_path: str,
    filename: str,
    chunk_size: int,
) -> dict[str, Any]:
    """
    Process a document upload job.

    This is called by the ARQ worker when a document upload is queued.
    """
    from pathlib import Path
    from src.jobs.document_worker import process_document_async
    from src.api.dependencies import get_doc_processor

    logger.info(f"Worker processing document job {job_id}: {filename}")

    try:
        doc_processor = get_doc_processor()

        result = await process_document_async(
            job_id=job_id,
            file_path=Path(file_path),
            filename=filename,
            chunk_size=chunk_size,
            doc_processor=doc_processor,
        )

        return result

    except Exception as e:
        logger.error(f"Worker failed on job {job_id}: {e}")
        await job_manager.fail_job(job_id, str(e))
        raise


async def process_url_job(
    ctx: dict[str, Any],
    job_id: str,
    url: str,
    chunk_size: int,
) -> dict[str, Any]:
    """
    Process a URL processing job.

    This is called by the ARQ worker when a URL processing is queued.
    """
    from src.jobs.document_worker import process_url_async
    from src.api.dependencies import get_config, get_doc_processor

    logger.info(f"Worker processing URL job {job_id}: {url}")

    try:
        config = get_config()
        doc_processor = get_doc_processor()

        result = await process_url_async(
            job_id=job_id,
            url=url,
            chunk_size=chunk_size,
            config=config,
            doc_processor=doc_processor,
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
        process_document_job,
        process_url_job,
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
