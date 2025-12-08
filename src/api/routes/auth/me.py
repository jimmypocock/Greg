"""
Current user profile routes.

Provides endpoint for getting the current authenticated user's info.

Endpoints:
    GET /auth/me - Get current user info
"""

from fastapi import APIRouter

from src.auth import CurrentUser
from src.auth.schemas import UserRead

router = APIRouter()


# Routes


@router.get("/me", response_model=UserRead)
async def get_current_user_info(user: CurrentUser):
    """Get the current authenticated user's info."""
    return user
