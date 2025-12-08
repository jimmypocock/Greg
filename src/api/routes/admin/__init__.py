"""
Admin routes.

Combines user, invite, cost, and document management routes under /admin prefix.
"""

from fastapi import APIRouter

from src.api.routes.admin import costs, documents, invites, users

router = APIRouter(prefix="/admin", tags=["Admin"])

router.include_router(costs.router, prefix="/costs", tags=["Admin - Costs"])
router.include_router(documents.router, prefix="/documents", tags=["Admin - Documents"])
router.include_router(invites.router, prefix="/invites", tags=["Admin - Invites"])
router.include_router(users.router, prefix="/users", tags=["Admin - Users"])
