"""
Pydantic schemas for authentication.

Defines request/response schemas for auth endpoints and FastAPI-Users integration.
"""

import uuid
from typing import TYPE_CHECKING, Any, Optional

from fastapi_users import schemas
from pydantic import BaseModel, EmailStr, Field, field_validator

from src.database.models import UserRole

if TYPE_CHECKING:
    from src.database.models import RefreshToken, User


# Schemas

class AccessTokenResponse(BaseModel):
    """Access token response (from refresh)."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    """JSON login request."""

    email: EmailStr
    password: str


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class RefreshTokenRequest(BaseModel):
    """Request containing a refresh token (used for logout, refresh)."""

    refresh_token: str


class RegisterResponse(BaseModel):
    """Registration response."""

    id: str
    email: str
    role: str
    is_active: bool
    is_superuser: bool
    is_verified: bool

    @classmethod
    def from_model(cls, user: "User") -> "RegisterResponse":
        """Create response from User model."""
        return cls(
            id=str(user.id),
            email=user.email,
            role=user.role.value,
            is_active=user.is_active,
            is_superuser=user.is_superuser,
            is_verified=user.is_verified,
        )


class SessionListResponse(BaseModel):
    """List of active sessions."""

    sessions: list["SessionResponse"]
    count: int


class SessionResponse(BaseModel):
    """Session info response."""

    id: str
    created_at: str
    expires_at: str
    device_info: dict[str, Any] | None
    is_current: bool = False

    @classmethod
    def from_model(cls, token: "RefreshToken") -> "SessionResponse":
        """Create response from RefreshToken model."""
        return cls(
            id=str(token.id),
            created_at=token.created_at.isoformat(),
            expires_at=token.expires_at.isoformat(),
            device_info=token.device_info,
        )


class TokenResponse(BaseModel):
    """Login response with access and refresh tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserCreate(schemas.BaseUserCreate):
    """
    Schema for creating a new user.

    Includes invite_code for registration validation.
    """

    email: EmailStr
    password: str = Field(..., min_length=8)
    invite_code: str = Field(
        default="",
        description="Invite code for registration (not required for first user)",
    )
    role: UserRole = UserRole.USER

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets minimum requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    def create_update_dict(self) -> dict:
        """Override to exclude invite_code from user creation dict."""
        d = super().create_update_dict()
        d.pop("invite_code", None)
        return d

    def create_update_dict_superuser(self) -> dict:
        """Override to exclude invite_code from superuser creation dict."""
        d = super().create_update_dict_superuser()
        d.pop("invite_code", None)
        return d


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schema for reading user data."""

    role: UserRole

    class Config:
        from_attributes = True


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating user data."""

    role: Optional[UserRole] = None
