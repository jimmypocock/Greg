"""
Application lifespan management (startup/shutdown).
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.api.dependencies import (
    get_config,
    get_vector_store_manager,
    cleanup_resources,
)
from src.database import init_database, close_database
from src.llm.warmup import start_background_warmup

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle.

    Startup:
        - Initialize database connection
        - Initialize configuration
        - Set up vector store manager
        - Start background model warmup
        - Run initial cleanup

    Shutdown:
        - Close database connection
        - Clean up all resources
    """
    # Startup
    logger.info("Initializing Greg API...")

    try:
        # Initialize database
        logger.info("Connecting to database...")
        await init_database()

        # Initialize config (creates directories)
        config = get_config()

        # Initialize vector store manager
        vector_store_manager = get_vector_store_manager()

        logger.info("System ready - components will be initialized on first use")

        # Start warming up models in the background
        logger.info("Starting background model warmup...")
        start_background_warmup()

        # Run initial cleanup
        logger.info("Running initial vector store cleanup...")
        cleanup_stats = vector_store_manager.cleanup_old_stores(force=True)
        if "removed_by_age" in cleanup_stats:
            total_removed = len(cleanup_stats.get("removed_by_age", [])) + len(
                cleanup_stats.get("removed_by_count", [])
            )
            if total_removed > 0:
                logger.info(f"Initial cleanup removed {total_removed} old vector stores")

    except Exception as e:
        logger.error(f"Failed to initialize system: {e}")
        raise

    yield

    # Shutdown
    logger.info("Shutting down Greg API...")
    await close_database()
    cleanup_resources()
    logger.info("Shutdown complete")
