"""
FastAPI dependency injection.
"""

import logging
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.config.settings import Config
from src.database import get_session_dependency

logger = logging.getLogger(__name__)

# Config singleton
_config: Config | None = None


def get_config() -> Config:
    """Get the application configuration."""
    global _config
    if _config is None:
        _config = Config()
        _config.create_directories()
    return _config


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async for session in get_session_dependency():
        yield session
