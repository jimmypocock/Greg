"""
ARQ job queue configuration.

Provides Redis-backed job queue for background task processing.
"""

import logging
import os
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

logger = logging.getLogger(__name__)

# Global Redis pool
_redis_pool: ArqRedis | None = None


def get_redis_settings() -> RedisSettings:
    """
    Get Redis settings from environment.

    Returns:
        RedisSettings for ARQ.

    Raises:
        ConfigurationError: If REDIS_URL is not set.
    """
    from src.config.validation import get_required

    redis_url = get_required("REDIS_URL")

    # Parse Redis URL
    # Format: redis://[:password@]host[:port][/database]
    if redis_url.startswith("redis://"):
        redis_url = redis_url[8:]  # Remove redis://

    # Handle password
    password = None
    if "@" in redis_url:
        auth, redis_url = redis_url.rsplit("@", 1)
        if ":" in auth:
            password = auth.split(":", 1)[1]

    # Handle database
    database = 0
    if "/" in redis_url:
        redis_url, db_str = redis_url.rsplit("/", 1)
        try:
            database = int(db_str)
        except ValueError:
            pass

    # Handle host and port
    host = "localhost"
    port = 6379
    if ":" in redis_url:
        host, port_str = redis_url.rsplit(":", 1)
        try:
            port = int(port_str)
        except ValueError:
            pass
    else:
        host = redis_url

    return RedisSettings(
        host=host,
        port=port,
        password=password,
        database=database,
    )


async def get_redis_pool() -> ArqRedis:
    """
    Get or create the Redis connection pool.

    Returns:
        ArqRedis connection pool.
    """
    global _redis_pool

    if _redis_pool is None:
        settings = get_redis_settings()
        _redis_pool = await create_pool(settings)
        logger.info(f"Connected to Redis at {settings.host}:{settings.port}")

    return _redis_pool


async def close_redis_pool() -> None:
    """Close the Redis connection pool."""
    global _redis_pool

    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None
        logger.info("Redis connection closed")


async def enqueue_job(
    function_name: str,
    *args: Any,
    _job_id: str | None = None,
    _queue_name: str | None = None,
    _defer_by: float | None = None,
    **kwargs: Any,
) -> str | None:
    """
    Enqueue a job for background processing.

    Args:
        function_name: Name of the function to run.
        *args: Positional arguments for the function.
        _job_id: Optional job ID (generated if not provided).
        _queue_name: Optional queue name.
        _defer_by: Optional delay in seconds.
        **kwargs: Keyword arguments for the function.

    Returns:
        Job ID if enqueued successfully, None otherwise.
    """
    try:
        pool = await get_redis_pool()

        job = await pool.enqueue_job(
            function_name,
            *args,
            _job_id=_job_id,
            _queue_name=_queue_name,
            _defer_by=_defer_by,
            **kwargs,
        )

        if job:
            logger.info(f"Enqueued job {job.job_id}: {function_name}")
            return job.job_id

        return None

    except Exception as e:
        logger.error(f"Failed to enqueue job {function_name}: {e}")
        return None
