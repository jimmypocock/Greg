"""
User registration routes.

Provides user registration endpoint.

Endpoints:
    POST /auth/register - Register with invite code
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request, status

from packages.core.auth.schemas import RegisterResponse, UserCreate
from packages.core.auth.users import UserManager, get_user_manager

logger = logging.getLogger(__name__)

router = APIRouter()


# Routes


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: Request,
    user_create: UserCreate,
    user_manager: Annotated[UserManager, Depends(get_user_manager)],
):
    """
    Register a new user with an invite code.

    The first user to register becomes a superuser/admin automatically.
    Subsequent users require a valid invite code.
    """
    created_user = await user_manager.register_user(user_create, request)

    logger.info(f"User registered: {created_user.email}")

    return RegisterResponse.from_model(created_user)
