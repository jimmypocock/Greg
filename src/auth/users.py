"""
FastAPI-Users configuration.

Provides user management, authentication strategies, and route setup.
"""

import os
import secrets
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users.db import SQLAlchemyUserDatabase
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import User, UserRole, get_session_dependency, Invite


# Configuration
SECRET_KEY = os.environ.get("JWT_SECRET_KEY", secrets.token_urlsafe(32))
ACCESS_TOKEN_EXPIRE_SECONDS = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "15")) * 60


async def get_user_db(session: AsyncSession = Depends(get_session_dependency)):
    """Get the SQLAlchemy user database adapter."""
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """
    Custom user manager with invite code validation and first-user admin logic.
    """

    reset_password_token_secret = SECRET_KEY
    verification_token_secret = SECRET_KEY

    def __init__(self, user_db: SQLAlchemyUserDatabase, session: AsyncSession):
        super().__init__(user_db)
        self.session = session

    async def on_after_register(self, user: User, request: Optional[Request] = None):
        """Called after a user registers."""
        # Log registration
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"User registered: {user.email} (admin={user.is_superuser})")

    async def on_after_login(
        self,
        user: User,
        request: Optional[Request] = None,
        response=None,
    ):
        """Called after a successful login."""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"User logged in: {user.email}")

    async def validate_invite_code(self, invite_code: str, email: str) -> Optional[Invite]:
        """
        Validate an invite code for registration.

        Returns the Invite if valid, None otherwise.
        """
        result = await self.session.execute(
            select(Invite).where(
                Invite.code == invite_code,
                Invite.is_active == True,
                Invite.used_by == None,
            )
        )
        invite = result.scalar_one_or_none()

        if not invite:
            return None

        # Check if invite is locked to specific email
        if invite.email and invite.email.lower() != email.lower():
            return None

        # Check if expired
        if invite.expires_at and datetime.now(timezone.utc) > invite.expires_at:
            return None

        return invite

    async def mark_invite_used(self, invite: Invite, user_id: uuid.UUID):
        """Mark an invite as used by a user."""
        invite.used_by = user_id
        invite.used_at = datetime.now(timezone.utc)

    async def is_first_user(self) -> bool:
        """Check if this would be the first user in the system."""
        user_count = await self.session.scalar(select(func.count(User.id)))
        return user_count == 0


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
    session: AsyncSession = Depends(get_session_dependency),
):
    """Get the user manager instance."""
    yield UserManager(user_db, session)


# Authentication backends
bearer_transport = BearerTransport(tokenUrl="auth/login")


def get_jwt_strategy() -> JWTStrategy:
    """Get JWT strategy for access tokens."""
    return JWTStrategy(
        secret=SECRET_KEY,
        lifetime_seconds=ACCESS_TOKEN_EXPIRE_SECONDS,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


# FastAPI-Users instance
fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# Dependency shortcuts
current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
current_verified_user = fastapi_users.current_user(active=True, verified=True)
optional_current_user = fastapi_users.current_user(active=True, optional=True)
