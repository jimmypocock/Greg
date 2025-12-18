"""
User model for authentication.

Uses FastAPI-Users with custom role field and subscription plan.
"""

from datetime import datetime
from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Optional

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from packages.core.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from packages.core.database.models.api_key import APIKey
    from packages.core.database.models.invite import Invite
    from packages.core.database.models.refresh_token import RefreshToken


class UserRole(str, PyEnum):
    """User roles for access control."""

    USER = "user"
    ADMIN = "admin"


class UserPlan(str, PyEnum):
    """Subscription plans with different AI usage limits."""

    FREE = "free"       # 10 AI credits/month
    PRO = "pro"         # 200 AI credits/month
    ENTERPRISE = "enterprise"  # 500 AI credits/month


# AI credit limits per plan per month
PLAN_CREDITS = {
    UserPlan.FREE: 10,
    UserPlan.PRO: 200,
    UserPlan.ENTERPRISE: 500,
}


class User(SQLAlchemyBaseUserTableUUID, TimestampMixin, Base):
    """
    User account model.

    Extends FastAPI-Users base table with custom role field and subscription plan.
    FastAPI-Users provides: id, email, hashed_password, is_active, is_superuser, is_verified
    """

    __tablename__ = "users"

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole),
        default=UserRole.USER,
        nullable=False,
    )

    # Subscription plan
    plan: Mapped[UserPlan] = mapped_column(
        Enum(UserPlan),
        default=UserPlan.FREE,
        nullable=False,
    )

    # Stripe customer/subscription IDs (nullable for free users)
    stripe_customer_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Subscription dates
    plan_started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    plan_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # AI usage tracking for current billing period
    ai_credits_used: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    ai_credits_reset_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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
    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        "RefreshToken",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN or self.is_superuser

    @property
    def ai_credits_limit(self) -> int:
        """Get AI credits limit for user's current plan."""
        return PLAN_CREDITS.get(self.plan, PLAN_CREDITS[UserPlan.FREE])

    @property
    def ai_credits_remaining(self) -> int:
        """Get remaining AI credits for current billing period."""
        return max(0, self.ai_credits_limit - self.ai_credits_used)

    @property
    def has_ai_credits(self) -> bool:
        """Check if user has remaining AI credits."""
        # Admins have unlimited credits
        if self.is_admin:
            return True
        return self.ai_credits_remaining > 0

    def to_dict(self) -> dict:
        """Convert to dictionary (for API responses)."""
        return {
            "id": str(self.id),
            "email": self.email,
            "role": self.role.value,
            "plan": self.plan.value,
            "is_active": self.is_active,
            "is_superuser": self.is_superuser,
            "is_verified": self.is_verified,
            "ai_credits_used": self.ai_credits_used,
            "ai_credits_limit": self.ai_credits_limit,
            "ai_credits_remaining": self.ai_credits_remaining,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
