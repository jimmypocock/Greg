"""
FastAPI-Users configuration.

Provides user management, authentication strategies, and route setup.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from api.auth.schemas import UserCreate

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

from api.auth.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    InvalidInviteCodeError,
    InvalidTokenError,
    UserDisabledError,
    UserNotFoundError,
)
from api.database import Invite, User, UserRole, get_session_dependency

# Constants

from api.config import Config
from api.config.validation import get_required

ACCESS_TOKEN_EXPIRE_SECONDS = Config.ACCESS_TOKEN_EXPIRE_MINUTES * 60
SECRET_KEY = get_required("JWT_SECRET_KEY")

logger = logging.getLogger(__name__)


# Data classes


@dataclass
class Credentials:
    """Credentials for authentication."""

    username: str
    password: str


@dataclass
class LoginResult:
    """Result of a successful login."""

    user: User
    access_token: str
    refresh_token: str


# Classes

class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    """Custom user manager with invite code validation and first-user admin logic."""

    reset_password_token_secret = SECRET_KEY
    verification_token_secret = SECRET_KEY

    def __init__(self, user_db: SQLAlchemyUserDatabase, session: AsyncSession):
        super().__init__(user_db)
        self.session = session

    async def is_first_user(self) -> bool:
        """Check if this would be the first user in the system."""
        user_count = await self.session.scalar(select(func.count(User.id)))
        return user_count == 0

    async def login(
        self,
        email: str,
        password: str,
        device_info: dict[str, Any] | None = None,
        request: Optional[Request] = None,
    ) -> LoginResult:
        """
        Authenticate user and generate tokens.

        Args:
            email: User email
            password: User password
            device_info: Optional device/session metadata
            request: Optional request for hooks

        Returns:
            LoginResult with user and tokens

        Raises:
            InvalidCredentialsError: If email/password is wrong
            UserDisabledError: If user account is disabled
        """
        from api.auth.refresh_tokens import create_refresh_token

        credentials = Credentials(username=email, password=password)
        user = await self.authenticate(credentials)

        if not user:
            raise InvalidCredentialsError()

        if not user.is_active:
            raise UserDisabledError()

        jwt_strategy = get_jwt_strategy()
        access_token = await jwt_strategy.write_token(user)

        refresh_token_plain, _ = await create_refresh_token(
            self.session,
            user,
            device_info=device_info,
        )

        await self.on_after_login(user, request)

        return LoginResult(
            user=user,
            access_token=access_token,
            refresh_token=refresh_token_plain,
        )

    async def refresh_tokens(
        self,
        refresh_token: str,
        device_info: dict[str, Any] | None = None,
    ) -> LoginResult:
        """
        Refresh access token using a refresh token.

        Args:
            refresh_token: The refresh token to validate and rotate
            device_info: Optional device/session metadata

        Returns:
            LoginResult with user and new tokens

        Raises:
            InvalidTokenError: If refresh token is invalid/expired/revoked
            UserNotFoundError: If user no longer exists
            UserDisabledError: If user account is disabled
        """
        from api.auth.refresh_tokens import rotate_refresh_token, validate_refresh_token

        token_record = await validate_refresh_token(self.session, refresh_token)

        if not token_record:
            raise InvalidTokenError("Invalid or expired refresh token")

        result = await self.session.execute(
            select(User).where(User.id == token_record.user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            raise UserNotFoundError()

        if not user.is_active:
            raise UserDisabledError()

        jwt_strategy = get_jwt_strategy()
        access_token = await jwt_strategy.write_token(user)

        new_refresh_token_plain, _ = await rotate_refresh_token(
            self.session,
            token_record,
            device_info=device_info,
        )

        return LoginResult(
            user=user,
            access_token=access_token,
            refresh_token=new_refresh_token_plain,
        )

    async def mark_invite_used(self, invite: Invite, user_id: uuid.UUID) -> None:
        """Mark an invite as used by a user."""
        from api.database.models import InviteType

        if invite.type == InviteType.REFERRAL:
            # For referral invites, increment use count (don't set used_by)
            invite.use_count += 1
        else:
            # For single-use invites, mark as used
            invite.used_by = user_id
            invite.used_at = datetime.now(timezone.utc)

    async def register_user(
        self,
        user_create: "UserCreate",
        request: Optional[Request] = None,
    ) -> User:
        """
        Register a new user.

        Handles first-user admin logic and invite code validation.
        For referral invites, links the new user and credits the referrer.

        Args:
            user_create: User registration data
            request: Optional request for hooks

        Returns:
            Created user

        Raises:
            InvalidInviteCodeError: If invite code is invalid (non-first user)
            EmailAlreadyExistsError: If email is already registered
        """
        from api.database.models import InviteType

        is_first_user = await self.is_first_user()

        if is_first_user:
            user_create.is_superuser = True
            user_create.role = UserRole.ADMIN
            invite = None
        else:
            invite = await self.validate_invite_code(
                user_create.invite_code,
                user_create.email,
            )
            if not invite:
                raise InvalidInviteCodeError()

        try:
            created_user = await self.create(
                user_create,
                safe=True,
                request=request,
            )
        except Exception as e:
            error_msg = str(e)
            if "UNIQUE constraint" in error_msg or "duplicate key" in error_msg.lower():
                raise EmailAlreadyExistsError()
            raise

        if invite:
            # Mark invite as used
            await self.mark_invite_used(invite, created_user.id)

            # Handle referral-specific logic
            if invite.type == InviteType.REFERRAL:
                # Link user to the referral invite
                created_user.referred_by_invite_id = invite.id

                # Credit the referrer
                if invite.created_by and invite.referrer_credits > 0:
                    referrer = await self.session.get(User, invite.created_by)
                    if referrer:
                        # Reduce credits used (effectively giving free credits)
                        referrer.ai_credits_used = max(
                            0, referrer.ai_credits_used - invite.referrer_credits
                        )
                        logger.info(
                            f"Credited {invite.referrer_credits} credits to referrer "
                            f"{referrer.email} for referring {created_user.email}"
                        )

            await self.session.commit()

        return created_user

    async def on_after_login(
        self,
        user: User,
        request: Optional[Request] = None,
        response=None,
    ) -> None:
        """Called after a successful login."""
        logger.info(f"User logged in: {user.email}")

    async def on_after_register(
        self,
        user: User,
        request: Optional[Request] = None,
    ) -> None:
        """Called after a user registers."""
        logger.info(f"User registered: {user.email} (admin={user.is_superuser})")

    async def validate_invite_code(
        self,
        invite_code: str,
        email: str,
    ) -> Optional[Invite]:
        """
        Validate an invite code for registration.

        Returns the Invite if valid, None otherwise.
        Handles both single-use invites and multi-use referral codes.
        """
        from api.database.models import InviteType

        result = await self.session.execute(
            select(Invite).where(
                Invite.code == invite_code,
                Invite.is_active == True,
            )
        )
        invite = result.scalar_one_or_none()

        if not invite:
            return None

        # Check if invite is expired
        if invite.expires_at and datetime.now(timezone.utc) > invite.expires_at:
            return None

        # For referral invites, check max_uses
        if invite.type == InviteType.REFERRAL:
            if invite.max_uses is not None and invite.use_count >= invite.max_uses:
                return None
        else:
            # For regular invites, must not be used
            if invite.used_by is not None:
                return None

        # Check email restriction
        if invite.email and invite.email.lower() != email.lower():
            return None

        return invite


# Authentication setup

bearer_transport = BearerTransport(tokenUrl="auth/token")


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


# Dependency providers

async def get_user_db(
    session: AsyncSession = Depends(get_session_dependency),
):
    """Get the SQLAlchemy user database adapter."""
    yield SQLAlchemyUserDatabase(session, User)


async def get_user_manager(
    user_db: SQLAlchemyUserDatabase = Depends(get_user_db),
    session: AsyncSession = Depends(get_session_dependency),
):
    """Get the user manager instance."""
    yield UserManager(user_db, session)


# FastAPI-Users instance

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])


# Dependency shortcuts

current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)
current_verified_user = fastapi_users.current_user(active=True, verified=True)
optional_current_user = fastapi_users.current_user(active=True, optional=True)
