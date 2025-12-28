"""
SongShareLink model.
"""

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Boolean, Enum, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database.models.base import Base
from api.enums import CollaboratorRole


def generate_share_token() -> str:
    """Generate a secure, URL-safe share token."""
    return secrets.token_urlsafe(32)


class SongShareLink(Base):
    """A shareable link that grants access to a song. Immutable - no updated_at."""

    __tablename__ = "song_share_links"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    song_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("songs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Unique token for the share link
    token: Mapped[str] = mapped_column(
        String(64),
        default=generate_share_token,
        nullable=False,
        unique=True,
        index=True,
    )

    # What role does this link grant?
    role: Mapped[CollaboratorRole] = mapped_column(
        Enum(CollaboratorRole, name="collaboratorrole", create_type=False),
        default=CollaboratorRole.VIEWER,
        nullable=False,
    )

    # Who created this link
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    # Optional expiration
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Usage limits
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)  # null = unlimited
    use_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Can be deactivated without deleting
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamp (no updated_at - share links are immutable once created)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        status = "valid" if self.is_valid else "invalid"
        return f"<SongShareLink {self.token[:8]}... ({self.role.value}, {status})>"

    @property
    def is_expired(self) -> bool:
        """Check if the link has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_exhausted(self) -> bool:
        """Check if the link has reached its usage limit."""
        if self.max_uses is None:
            return False
        return self.use_count >= self.max_uses

    @property
    def is_valid(self) -> bool:
        """Check if the link can still be used."""
        return self.is_active and not self.is_expired and not self.is_exhausted

    def increment_use_count(self) -> None:
        """Increment the usage counter."""
        self.use_count += 1
