"""
Admin document management routes.

Provides admin-only endpoints for document management.

Endpoints:
    DELETE /admin/documents - Clear all documents
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends

from src.api.dependencies import get_config
from src.auth import AdminUser
from src.config.settings import Config
from src.database import get_session_dependency
from src.documents import DocumentService, MessageResponse
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependencies


async def get_document_service(
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
    config: Annotated[Config, Depends(get_config)],
) -> DocumentService:
    """Get document service with session and config."""
    return DocumentService(session=session, config=config)


# Routes


@router.delete("", response_model=MessageResponse)
async def clear_all_documents(
    admin: AdminUser,
    config: Annotated[Config, Depends(get_config)],
    service: Annotated[DocumentService, Depends(get_document_service)],
):
    """Clear all documents and chunks. Admin only."""
    await service.delete_all_documents(config.UPLOAD_DIR)

    logger.info(f"Admin {admin.email} cleared all documents")

    return MessageResponse(message="All documents cleared successfully")
