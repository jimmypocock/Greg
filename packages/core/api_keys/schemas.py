"""
Pydantic schemas for API key management.

Defines request/response schemas for API key endpoints.
"""

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from packages.core.database import APIKey


# Schemas


class APIKeyCreateRequest(BaseModel):
    """Request to create a new API key."""

    name: str = Field(..., min_length=1, max_length=100)


class APIKeyCreateResponse(BaseModel):
    """
    Response after creating an API key.

    IMPORTANT: The 'key' field is only returned once at creation time.
    Store it securely - it cannot be retrieved again.
    """

    id: str
    key: str
    key_prefix: str
    message: str = "Store this key securely - it won't be shown again"
    name: str


class APIKeyListResponse(BaseModel):
    """Response containing list of API keys."""

    api_keys: list["APIKeyResponse"]
    count: int


class APIKeyResponse(BaseModel):
    """API key info (without the actual key)."""

    id: str
    key_prefix: str
    name: str
    created_at: str
    is_active: bool
    last_used_at: str | None

    @classmethod
    def from_model(cls, key: "APIKey") -> "APIKeyResponse":
        """Create response from APIKey model."""
        return cls(
            id=str(key.id),
            key_prefix=key.key_prefix,
            name=key.name,
            created_at=key.created_at.isoformat(),
            is_active=key.is_active,
            last_used_at=key.last_used_at.isoformat() if key.last_used_at else None,
        )
