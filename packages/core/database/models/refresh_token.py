"""
Refresh Token model for secure session management.

Stores hashed refresh tokens with expiration and revocation support.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.core.database.models.base import Base

if TYPE_CHECKING:
    from packages.core.database.models.user import User


class RefreshToken(Base):
    """Database-backed refresh token for secure session management."""

    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Token hash (never store plain tokens)
    token_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
    )

    # Expiration
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    # Revocation (null = active)
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
    )

    # Session metadata
    device_info: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")

    @property
    def is_valid(self) -> bool:
        """Check if token is valid (not expired and not revoked)."""
        now = datetime.now(timezone.utc)
        return self.revoked_at is None and self.expires_at > now

    @property
    def is_expired(self) -> bool:
        """Check if token has expired."""
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_revoked(self) -> bool:
        """Check if token has been revoked."""
        return self.revoked_at is not None

    def revoke(self) -> None:
        """Revoke this token."""
        self.revoked_at = datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (for API responses)."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "expires_at": self.expires_at.isoformat(),
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "device_info": self.device_info,
            "created_at": self.created_at.isoformat(),
            "is_valid": self.is_valid,
        }
