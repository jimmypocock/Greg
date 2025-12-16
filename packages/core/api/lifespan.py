"""
Application lifespan management (startup/shutdown).
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from packages.core.api.dependencies import get_config
from packages.core.database import init_database, close_database

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.

    Startup:
        - Initialize database connection
        - Initialize configuration

    Shutdown:
        - Close database connection
    """
    # Startup
    logger.info("Initializing Greg API...")

    try:
        # Initialize database
        logger.info("Connecting to database...")
        await init_database()

        # Initialize config (creates directories)
        get_config()

        logger.info("System ready")

    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Greg API...")
    await close_database()
    logger.info("Shutdown complete")
