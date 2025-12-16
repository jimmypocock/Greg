"""
API key service.

Handles API key CRUD operations.
"""

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.api_keys.exceptions import APIKeyNotFoundError
from packages.core.auth import generate_api_key
from packages.core.database import APIKey

if TYPE_CHECKING:
    from packages.core.api_keys.schemas import APIKeyCreateRequest
    from packages.core.database.models import User


class APIKeyResult:
    """Result of API key creation."""

    def __init__(self, api_key: APIKey, full_key: str):
        self.api_key = api_key
        self.full_key = full_key


class APIKeyService:
    """
    API key service for CRUD operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_keys(self, user_id: uuid.UUID) -> list[APIKey]:
        """List all active API keys for a user."""
        result = await self.session.execute(
            select(APIKey)
            .where(APIKey.user_id == user_id, APIKey.is_active == True)
            .order_by(APIKey.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_key(
        self,
        user: "User",
        request: "APIKeyCreateRequest",
    ) -> APIKeyResult:
        """Create a new API key."""
        full_key, key_hash, key_prefix = generate_api_key()

        api_key = APIKey(
            key_hash=key_hash,
            key_prefix=key_prefix,
            name=request.name,
            user_id=user.id,
        )
        self.session.add(api_key)
        await self.session.commit()
        await self.session.refresh(api_key)

        return APIKeyResult(api_key, full_key)

    async def revoke_key(self, key_id: uuid.UUID, user_id: uuid.UUID) -> APIKey:
        """Revoke an API key."""
        result = await self.session.execute(
            select(APIKey).where(
                APIKey.id == key_id,
                APIKey.user_id == user_id,
            )
        )
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise APIKeyNotFoundError(str(key_id))

        api_key.is_active = False
        await self.session.commit()

        return api_key


async def get_api_key_service(session: AsyncSession) -> APIKeyService:
    """Factory function for API key service."""
    return APIKeyService(session=session)
