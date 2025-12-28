"""
Invite model for referrals, collaboration, and promotions.

Invite types:
- referral: Users share codes to earn credits when friends sign up
- collaboration: Invite non-users to collaborate on a specific song
- promo: Partnership/marketing codes for bonuses
"""

import enum
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from api.database.models.user import User


class InviteType(str, enum.Enum):
    """Type of invite."""

    REFERRAL = "referral"
    COLLABORATION = "collaboration"
    PROMO = "promo"


class Invite(Base, TimestampMixin):
    """Invite code for referrals, collaboration, and promotions."""

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
    type: Mapped[InviteType] = mapped_column(
        Enum(InviteType, name="invitetype", create_type=False),
        nullable=False,
        default=InviteType.REFERRAL,
    )

    # Who created the invite (null for system-generated promo codes)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # For collaboration invites: which song and what role
    song_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
    )
    collaboration_role: Mapped[Optional[str]] = mapped_column(
        Enum("viewer", "editor", "admin", name="collaboratorrole", create_type=False),
        nullable=True,
    )

    # Credit rewards
    referrer_credits: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    bonus_credits: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Usage limits
    max_uses: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,  # null = unlimited
    )
    use_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    # Validity
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Optional target email for personalized invites
    email: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Promo metadata
    promo_name: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    def __repr__(self) -> str:
        status = "active" if self.is_active else "inactive"
        return f"<Invite '{self.code}' ({self.type.value}, {status})>"

    # Relationships
    created_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="created_invites",
        foreign_keys=[created_by],
    )
    referred_users: Mapped[list["User"]] = relationship(
        "User",
        back_populates="referred_by_invite",
        foreign_keys="User.referred_by_invite_id",
    )

    @property
    def is_expired(self) -> bool:
        """Check if the invite has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_exhausted(self) -> bool:
        """Check if the invite has reached its usage limit."""
        if self.max_uses is None:
            return False
        return self.use_count >= self.max_uses

    @property
    def is_valid(self) -> bool:
        """Check if invite can still be used."""
        return self.is_active and not self.is_expired and not self.is_exhausted

    def increment_use_count(self) -> None:
        """Increment the usage counter."""
        self.use_count += 1

    def to_dict(self) -> dict:
        """Convert to dictionary (for API responses)."""
        return {
            "id": str(self.id),
            "code": self.code,
            "type": self.type.value,
            "created_by": str(self.created_by) if self.created_by else None,
            "song_id": str(self.song_id) if self.song_id else None,
            "collaboration_role": self.collaboration_role,
            "referrer_credits": self.referrer_credits,
            "bonus_credits": self.bonus_credits,
            "max_uses": self.max_uses,
            "use_count": self.use_count,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_active": self.is_active,
            "is_valid": self.is_valid,
            "email": self.email,
            "promo_name": self.promo_name,
            "created_at": self.created_at.isoformat(),
        }
