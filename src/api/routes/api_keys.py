"""
API key management routes.

Endpoints:
    POST   /api-keys          - Create a new API key
    GET    /api-keys          - List user's API keys
    DELETE /api-keys/{key_id} - Revoke an API key
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import CurrentUser, generate_api_key
from src.database import APIKey, User, get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


# Request/Response schemas
class APIKeyCreateRequest(BaseModel):
    """API key creation request."""

    name: str
    expires_in_days: Optional[int] = None  # None = never expires


class APIKeyCreateResponse(BaseModel):
    """
    API key creation response.

    IMPORTANT: The 'key' field is only returned once at creation time.
    Store it securely - it cannot be retrieved again.
    """

    id: str
    key: str  # Only shown once!
    key_prefix: str
    name: str
    expires_at: Optional[str]
    message: str = "Store this key securely - it won't be shown again"


class APIKeyResponse(BaseModel):
    """API key info (without the actual key)."""

    id: str
    key_prefix: str
    name: str
    last_used_at: Optional[str]
    expires_at: Optional[str]
    is_active: bool
    created_at: str


class APIKeyListResponse(BaseModel):
    """List of API keys."""

    api_keys: list[APIKeyResponse]


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


@router.post("/", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: APIKeyCreateRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session_dependency),
):
    """
    Create a new API key.

    The full key is only returned once at creation time.
    Store it securely - it cannot be retrieved again.
    """
    # Validate name
    if not request.name or len(request.name) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name must be 1-100 characters",
        )

    # Generate key
    full_key, key_hash, key_prefix = generate_api_key()

    # Calculate expiration
    expires_at = None
    if request.expires_in_days:
        expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)

    # Create API key record
    api_key = APIKey(
        key_hash=key_hash,
        key_prefix=key_prefix,
        name=request.name,
        user_id=user.id,
        expires_at=expires_at,
    )
    session.add(api_key)
    await session.commit()

    logger.info(f"User {user.email} created API key {key_prefix}")

    return APIKeyCreateResponse(
        id=str(api_key.id),
        key=full_key,
        key_prefix=key_prefix,
        name=request.name,
        expires_at=expires_at.isoformat() if expires_at else None,
    )


@router.get("/", response_model=APIKeyListResponse)
async def list_api_keys(
    user: CurrentUser,
    session: AsyncSession = Depends(get_session_dependency),
):
    """List all API keys for the current user."""
    result = await session.execute(
        select(APIKey)
        .where(APIKey.user_id == user.id)
        .order_by(APIKey.created_at.desc())
    )
    api_keys = result.scalars().all()

    return APIKeyListResponse(
        api_keys=[
            APIKeyResponse(
                id=str(key.id),
                key_prefix=key.key_prefix,
                name=key.name,
                last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
                expires_at=key.expires_at.isoformat() if key.expires_at else None,
                is_active=key.is_active,
                created_at=key.created_at.isoformat(),
            )
            for key in api_keys
        ]
    )


@router.delete("/{key_id}", response_model=MessageResponse)
async def revoke_api_key(
    key_id: UUID,
    user: CurrentUser,
    session: AsyncSession = Depends(get_session_dependency),
):
    """Revoke an API key."""
    result = await session.execute(
        select(APIKey).where(
            APIKey.id == key_id,
            APIKey.user_id == user.id,
        )
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found",
        )

    api_key.is_active = False
    await session.commit()

    logger.info(f"User {user.email} revoked API key {api_key.key_prefix}")

    return MessageResponse(message="API key revoked")
