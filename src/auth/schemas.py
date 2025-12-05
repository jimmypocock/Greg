"""
Pydantic schemas for FastAPI-Users.

Defines user create, read, and update schemas with custom fields.
"""

import uuid
from typing import Optional

from fastapi_users import schemas
from pydantic import EmailStr, Field, field_validator

from src.database.models import UserRole


class UserRead(schemas.BaseUser[uuid.UUID]):
    """Schema for reading user data."""

    role: UserRole

    class Config:
        from_attributes = True


class UserCreate(schemas.BaseUserCreate):
    """
    Schema for creating a new user.

    Includes invite_code for registration validation.
    """

    email: EmailStr
    password: str = Field(..., min_length=8)
    invite_code: str = Field(default="", description="Invite code for registration (not required for first user)")

    # Custom fields with defaults
    role: UserRole = UserRole.USER

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets minimum requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class UserUpdate(schemas.BaseUserUpdate):
    """Schema for updating user data."""

    role: Optional[UserRole] = None
