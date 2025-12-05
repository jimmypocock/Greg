"""
User model for authentication.

Uses FastAPI-Users with custom role field.
"""

from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.api_key import APIKey
    from src.database.models.invite import Invite


class UserRole(str, PyEnum):
    """User roles for access control."""

    USER = "user"
    ADMIN = "admin"


class User(SQLAlchemyBaseUserTableUUID, TimestampMixin, Base):
    """
    User account model.

    Extends FastAPI-Users base table with custom role field.
    FastAPI-Users provides: id, email, hashed_password, is_active, is_superuser, is_verified
    """

    __tablename__ = "users"

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.USER,
        nullable=False,
    )

    # Relationships
    api_keys: Mapped[list["APIKey"]] = relationship(
        "APIKey",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    created_invites: Mapped[list["Invite"]] = relationship(
        "Invite",
        back_populates="created_by_user",
        foreign_keys="Invite.created_by",
    )

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN or self.is_superuser
