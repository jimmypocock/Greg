"""
Refresh token service for secure session management.

Handles creation, validation, and revocation of database-backed refresh tokens.
"""

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import Config
from api.database.models import RefreshToken, User

# Constants

REFRESH_TOKEN_BYTES = 32  # 256 bits of entropy
REFRESH_TOKEN_EXPIRE_DAYS = Config.REFRESH_TOKEN_EXPIRE_DAYS
MAX_SESSIONS_PER_USER = Config.MAX_SESSIONS_PER_USER

logger = logging.getLogger(__name__)


# Public functions

async def cleanup_expired_tokens(session: AsyncSession) -> int:
    """
    Delete expired and revoked tokens from the database.

    Should be run periodically (e.g., daily cron job).

    Returns:
        Number of tokens deleted
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=1)  # Keep revoked tokens for 1 day for audit

    result = await session.execute(
        delete(RefreshToken).where(
            (RefreshToken.expires_at < now) |
            (RefreshToken.revoked_at < cutoff)
        )
    )

    await session.commit()

    count = result.rowcount
    if count > 0:
        logger.info(f"Cleaned up {count} expired/revoked refresh tokens")

    return count


async def create_refresh_token(
    session: AsyncSession,
    user: User,
    device_info: dict[str, Any] | None = None,
) -> tuple[str, RefreshToken]:
    """
    Create a new refresh token for a user.

    Args:
        session: Database session
        user: User to create token for
        device_info: Optional device/session metadata

    Returns:
        Tuple of (plain_token, refresh_token_record)
    """
    plain_token, token_hash = _generate_refresh_token()

    expires_at = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    refresh_token = RefreshToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        device_info=device_info,
    )

    session.add(refresh_token)

    await _enforce_session_limit(session, user.id)

    await session.commit()

    logger.info(f"Created refresh token for user {user.email}")

    return plain_token, refresh_token


async def get_active_refresh_tokens(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> list[RefreshToken]:
    """
    Get all active (non-revoked, non-expired) refresh tokens for a user.

    Args:
        session: Database session
        user_id: User ID

    Returns:
        List of active refresh tokens
    """
    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at == None,
            RefreshToken.expires_at > now,
        )
        .order_by(RefreshToken.created_at.desc())
    )

    return list(result.scalars().all())


async def revoke_all_user_tokens(
    session: AsyncSession,
    user_id: uuid.UUID,
    except_token: str | None = None,
) -> int:
    """
    Revoke all refresh tokens for a user (logout everywhere).

    Args:
        session: Database session
        user_id: User ID
        except_token: Optional token to keep active (current session)

    Returns:
        Number of tokens revoked
    """
    now = datetime.now(timezone.utc)

    query = select(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at == None,
    )

    if except_token:
        except_hash = _hash_token(except_token)
        query = query.where(RefreshToken.token_hash != except_hash)

    result = await session.execute(query)
    tokens = result.scalars().all()

    count = 0
    for token in tokens:
        token.revoked_at = now
        count += 1

    await session.commit()

    if count > 0:
        logger.info(f"Revoked {count} refresh tokens for user {user_id}")

    return count


async def revoke_user_session(
    session: AsyncSession,
    session_id: str,
    user_id: uuid.UUID,
) -> None:
    """
    Revoke a specific session for a user.

    Args:
        session: Database session
        session_id: Session ID (UUID string)
        user_id: User ID (must own the session)

    Raises:
        InvalidSessionIdError: If session_id is not a valid UUID
        SessionNotFoundError: If session doesn't exist or doesn't belong to user
        SessionAlreadyRevokedError: If session is already revoked
    """
    from api.auth.exceptions import (
        InvalidSessionIdError,
        SessionAlreadyRevokedError,
        SessionNotFoundError,
    )

    try:
        token_uuid = uuid.UUID(session_id)
    except ValueError:
        raise InvalidSessionIdError()

    result = await session.execute(
        select(RefreshToken).where(
            RefreshToken.id == token_uuid,
            RefreshToken.user_id == user_id,
        )
    )
    refresh_token = result.scalar_one_or_none()

    if not refresh_token:
        raise SessionNotFoundError()

    if refresh_token.is_revoked:
        raise SessionAlreadyRevokedError()

    refresh_token.revoke()
    await session.commit()

    logger.info(f"Revoked session {session_id} for user {user_id}")


async def revoke_refresh_token(
    session: AsyncSession,
    token: str,
) -> bool:
    """
    Revoke a specific refresh token (logout).

    Args:
        session: Database session
        token: Plain refresh token to revoke

    Returns:
        True if token was found and revoked, False otherwise
    """
    token_hash = _hash_token(token)

    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    refresh_token = result.scalar_one_or_none()

    if not refresh_token:
        return False

    if refresh_token.is_revoked:
        return True  # Already revoked

    refresh_token.revoke()
    await session.commit()

    logger.info(f"Revoked refresh token for user {refresh_token.user_id}")

    return True


async def rotate_refresh_token(
    session: AsyncSession,
    old_token: RefreshToken,
    device_info: dict[str, Any] | None = None,
) -> tuple[str, RefreshToken]:
    """
    Rotate a refresh token (revoke old, create new).

    This is a security best practice - each refresh token can only be used once.

    Args:
        session: Database session
        old_token: The current refresh token to rotate
        device_info: Optional device/session metadata for new token

    Returns:
        Tuple of (new_plain_token, new_refresh_token_record)
    """
    result = await session.execute(
        select(User).where(User.id == old_token.user_id)
    )
    user = result.scalar_one()

    old_token.revoke()

    new_device_info = device_info or old_token.device_info
    plain_token, new_token = await create_refresh_token(
        session, user, device_info=new_device_info
    )

    logger.info(f"Rotated refresh token for user {user.email}")

    return plain_token, new_token


async def validate_refresh_token(
    session: AsyncSession,
    token: str,
) -> RefreshToken | None:
    """
    Validate a refresh token and return the token record if valid.

    Args:
        session: Database session
        token: Plain refresh token from client

    Returns:
        RefreshToken if valid, None otherwise
    """
    token_hash = _hash_token(token)

    result = await session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )
    refresh_token = result.scalar_one_or_none()

    if not refresh_token:
        logger.warning("Refresh token not found")
        return None

    if refresh_token.is_revoked:
        logger.warning(f"Attempted use of revoked refresh token for user {refresh_token.user_id}")
        return None

    if refresh_token.is_expired:
        logger.warning(f"Attempted use of expired refresh token for user {refresh_token.user_id}")
        return None

    return refresh_token


# Private functions

async def _enforce_session_limit(
    session: AsyncSession,
    user_id: uuid.UUID,
) -> None:
    """
    Enforce maximum sessions per user by revoking oldest sessions.

    Args:
        session: Database session
        user_id: User ID
    """
    now = datetime.now(timezone.utc)

    result = await session.execute(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at == None,
            RefreshToken.expires_at > now,
        )
        .order_by(RefreshToken.created_at.asc())
    )
    active_tokens = list(result.scalars().all())

    excess = len(active_tokens) - MAX_SESSIONS_PER_USER + 1
    if excess > 0:
        for token in active_tokens[:excess]:
            token.revoked_at = now

        logger.info(f"Revoked {excess} oldest sessions for user {user_id} (session limit)")


def _generate_refresh_token() -> tuple[str, str]:
    """
    Generate a new refresh token.

    Returns:
        Tuple of (plain_token, token_hash)
        - plain_token: Send to client (only returned once)
        - token_hash: Store in database
    """
    plain_token = secrets.token_urlsafe(REFRESH_TOKEN_BYTES)
    token_hash = _hash_token(plain_token)
    return plain_token, token_hash


def _hash_token(token: str) -> str:
    """Hash a token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()
