"""
Pydantic schemas for admin management.

Defines request/response schemas for admin endpoints.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


# Request schemas


class InviteCreateRequest(BaseModel):
    """Invite creation request body."""

    email: EmailStr | None = None
    expires_in_days: int | None = 7


class UserUpdateRequest(BaseModel):
    """User update request body."""

    is_active: bool | None = None
    role: str | None = None


# Response schemas


class InviteDetail(BaseModel):
    """Invite details for API responses."""

    code: str
    email: str | None
    is_active: bool
    created_at: datetime
    expires_at: datetime | None
    used_at: datetime | None
    used_by: UUID | None
    created_by: UUID


class InviteResponse(BaseModel):
    """Single invite response with signup URL."""

    invite: InviteDetail
    signup_url: str | None = None


class InviteListResponse(BaseModel):
    """Paginated invite list response."""

    invites: list[InviteDetail]
    total: int


class UserDetail(BaseModel):
    """User details for API responses."""

    id: UUID
    email: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime


class UserResponse(BaseModel):
    """Single user response."""

    user: UserDetail


class UserListResponse(BaseModel):
    """Paginated user list response."""

    users: list[UserDetail]
    total: int


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str
