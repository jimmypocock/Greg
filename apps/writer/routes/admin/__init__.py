"""
Admin routes (writer app).

Writer-specific admin routes for document management.
"""

from fastapi import APIRouter

from apps.writer.routes.admin import documents

router = APIRouter(prefix="/admin", tags=["Admin - Writer"])

router.include_router(documents.router, prefix="/documents", tags=["Admin - Documents"])
