"""
Database connection and session management.

Provides async SQLAlchemy engine and session factory for PostgreSQL.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from api.database.models import Base

logger = logging.getLogger(__name__)

# Global engine and session factory
_engine = None
_async_session_factory = None


def get_database_url() -> str:
    """
    Get database URL from environment.

    Returns:
        PostgreSQL connection URL for asyncpg.

    Raises:
        RuntimeError: If DATABASE_URL is not set.
    """
    from api.config.validation import get_required

    database_url = get_required("DATABASE_URL")

    # Convert postgres:// to postgresql+asyncpg://
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    return database_url


async def init_database(database_url: str | None = None) -> None:
    """
    Initialize the database engine and create tables.

    Args:
        database_url: Optional database URL. If not provided, uses environment.
    """
    global _engine, _async_session_factory

    if database_url is None:
        database_url = get_database_url()

    logger.info("Initializing database connection")

    _engine = create_async_engine(
        database_url,
        echo=False,  # Set to True for SQL logging
        poolclass=NullPool,  # Recommended for async
    )

    _async_session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    # Create tables if they don't exist
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("Database initialized")


async def close_database() -> None:
    """Close the database connection."""
    global _engine, _async_session_factory

    if _engine:
        await _engine.dispose()
        _engine = None
        _async_session_factory = None
        logger.info("Database connection closed")


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get an async database session.

    Usage:
        async with get_session() as session:
            result = await session.execute(select(User))
    """
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    session = _async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for database sessions.

    Usage:
        @router.get("/users")
        async def get_users(session: AsyncSession = Depends(get_session_dependency)):
            ...
    """
    if _async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")

    session = _async_session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
