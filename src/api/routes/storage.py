"""
Storage statistics routes.

Provides vector store statistics for monitoring.

Endpoints:
    GET /storage - Get vector store statistics
"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.auth import CurrentUser
from src.storage import StorageService, StorageStatsResponse

router = APIRouter()


# Routes


@router.get("/storage", response_model=StorageStatsResponse)
async def get_storage_stats(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_db)],
):
    """Get storage statistics for document chunks."""
    service = StorageService(session)
    return await service.get_stats(user.id)
