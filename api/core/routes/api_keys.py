"""
API key management routes.

Provides API key creation and management for programmatic access.

Endpoints:
    POST   /api-keys/          - Create a new API key
    GET    /api-keys/          - List user's API keys
    DELETE /api-keys/{key_id}  - Revoke an API key
"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.api_keys import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeyResponse,
    APIKeyService,
)
from api.auth import CurrentUser
from api.auth.schemas import MessageResponse
from api.database import get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


# Dependencies


async def get_api_key_service(
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
) -> APIKeyService:
    """Get API key service with session."""
    return APIKeyService(session=session)


# Routes


@router.post("/", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: APIKeyCreateRequest,
    user: CurrentUser,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
):
    """
    Create a new API key.

    The full key is only returned once at creation time.
    Store it securely - it cannot be retrieved again.
    """
    result = await service.create_key(user, request)

    logger.info(f"User {user.email} created API key {result.api_key.key_prefix}")

    return APIKeyCreateResponse(
        id=str(result.api_key.id),
        key=result.full_key,
        key_prefix=result.api_key.key_prefix,
        name=request.name,
    )


@router.get("/", response_model=APIKeyListResponse)
async def list_api_keys(
    user: CurrentUser,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
):
    """List all API keys for the current user."""
    keys = await service.list_keys(user.id)

    return APIKeyListResponse(
        api_keys=[APIKeyResponse.from_model(key) for key in keys],
        count=len(keys),
    )


@router.delete("/{key_id}", response_model=MessageResponse)
async def revoke_api_key(
    key_id: UUID,
    user: CurrentUser,
    service: Annotated[APIKeyService, Depends(get_api_key_service)],
):
    """Revoke an API key."""
    api_key = await service.revoke_key(key_id, user.id)

    logger.info(f"User {user.email} revoked API key {api_key.key_prefix}")

    return MessageResponse(message="API key revoked")
