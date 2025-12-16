"""
Pydantic schemas for admin management.

Defines request/response schemas for admin endpoints.
"""

from pydantic import BaseModel, EmailStr


# Schemas

class InviteCreateRequest(BaseModel):
    """Invite creation request body."""

    email: EmailStr | None = None
    expires_in_days: int | None = 7


class InviteListResponse(BaseModel):
    """Invite list response."""

    invites: list[dict]
    total: int


class InviteResponse(BaseModel):
    """Single invite response."""

    code: str
    email: str | None
    expires_at: str | None
    signup_url: str


class MessageResponse(BaseModel):
    """Simple message response."""

    message: str


class UserListResponse(BaseModel):
    """User list response."""

    total: int
    users: list[dict]


class UserResponse(BaseModel):
    """Single user response."""

    user: dict


class UserUpdateRequest(BaseModel):
    """User update request body."""

    is_active: bool | None = None
    role: str | None = None
