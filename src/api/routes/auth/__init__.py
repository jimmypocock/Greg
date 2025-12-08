"""
Authentication routes.

Combines token, registration, profile, session, and user management routes under /auth prefix.
"""

from fastapi import APIRouter

from src.api.routes.auth import me, registration, sessions, token, users

router = APIRouter(prefix="/auth", tags=["Auth"])

# Token operations (login, logout, refresh)
router.include_router(token.router)

# Registration
router.include_router(registration.router)

# Current user profile
router.include_router(me.router)

# Session management
router.include_router(sessions.router, prefix="/sessions", tags=["Auth - Sessions"])

# User management (fastapi-users)
router.include_router(users.router, prefix="/users", tags=["Auth - Users"])
