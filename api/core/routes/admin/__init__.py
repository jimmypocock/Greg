"""
Admin routes (core).

Core admin routes for user, invite, and cost management under /admin prefix.
"""

from fastapi import APIRouter

from api.core.routes.admin import costs, invites, users

router = APIRouter(prefix="/admin", tags=["Admin"])

router.include_router(costs.router, prefix="/costs", tags=["Admin - Costs"])
router.include_router(invites.router, prefix="/invites", tags=["Admin - Invites"])
router.include_router(users.router, prefix="/users", tags=["Admin - Users"])
