"""
Invite model for user registration.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.database.models.user import User


class Invite(Base, TimestampMixin):
    """Invite code for user registration."""

    __tablename__ = "invites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(
        String(32),
        unique=True,
        nullable=False,
        index=True,
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )
    used_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    created_by_user: Mapped["User"] = relationship(
        "User",
        back_populates="created_invites",
        foreign_keys=[created_by],
    )
    used_by_user: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[used_by],
    )

    @property
    def is_valid(self) -> bool:
        """Check if invite is still valid."""
        if not self.is_active:
            return False
        if self.used_by is not None:
            return False
        if self.expires_at and datetime.now(self.expires_at.tzinfo) > self.expires_at:
            return False
        return True
