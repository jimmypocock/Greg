"""
Health routes.

Endpoints:
    GET /health       - Liveness probe (is the process alive?)
    GET /health/ready - Readiness probe (can we serve traffic?)
"""

import logging

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])


# Public functions

@router.get("")
async def health():
    """
    Liveness probe.

    Returns 200 if the process is alive. Used by orchestrators
    to determine if the container needs to be restarted.
    """
    return {"status": "ok"}


@router.get("/ready")
async def health_ready():
    """
    Readiness probe.

    Checks if the service can accept traffic by verifying
    critical dependencies (database, redis) are reachable.
    Returns 503 if any dependency is unavailable.
    """
    checks = {}
    all_ok = True

    # Check database
    try:
        from sqlalchemy import text

        from src.database import get_session

        async with get_session() as session:
            await session.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = "error"
        all_ok = False

    # Check Redis
    try:
        from src.jobs.queue import get_redis_pool

        redis = await get_redis_pool()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        checks["redis"] = "error"
        all_ok = False

    response_data = {
        "status": "ok" if all_ok else "error",
        "checks": checks,
    }

    if all_ok:
        return response_data
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=response_data,
        )
