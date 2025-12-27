"""
AI credits management service.

Handles checking, consuming, and resetting AI credits based on user plan.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.database.models import User, UserPlan, PLAN_CREDITS

logger = logging.getLogger(__name__)


class InsufficientCreditsError(Exception):
    """Raised when user doesn't have enough AI credits."""

    def __init__(
        self,
        user_id: UUID,
        credits_used: int,
        credits_limit: int,
        plan: UserPlan,
    ):
        self.user_id = user_id
        self.credits_used = credits_used
        self.credits_limit = credits_limit
        self.plan = plan
        self.message = (
            f"AI credit limit reached. "
            f"Used {credits_used}/{credits_limit} credits this month. "
            f"Upgrade to Pro for more credits."
        )
        super().__init__(self.message)


class AICreditsService:
    """
    Service for managing AI credits.

    Credits reset monthly based on when the user's billing period started.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_user(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def check_credits(self, user_id: UUID) -> bool:
        """
        Check if user has available AI credits.

        Returns True if user can use AI features.
        Raises InsufficientCreditsError if limit reached.
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Admins have unlimited credits
        if user.is_admin:
            return True

        # Check if credits need to be reset (monthly)
        await self._maybe_reset_credits(user)

        # Check if user has credits remaining
        if not user.has_ai_credits:
            raise InsufficientCreditsError(
                user_id=user_id,
                credits_used=user.ai_credits_used,
                credits_limit=user.ai_credits_limit,
                plan=user.plan,
            )

        return True

    async def consume_credit(self, user_id: UUID, amount: int = 1) -> int:
        """
        Consume AI credits for a user.

        Args:
            user_id: User ID
            amount: Number of credits to consume (default 1)

        Returns:
            New credits used count

        Raises:
            InsufficientCreditsError if not enough credits
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Admins don't consume credits
        if user.is_admin:
            return 0

        # Check if credits need reset
        await self._maybe_reset_credits(user)

        # Check if user has enough credits
        if user.ai_credits_remaining < amount:
            raise InsufficientCreditsError(
                user_id=user_id,
                credits_used=user.ai_credits_used,
                credits_limit=user.ai_credits_limit,
                plan=user.plan,
            )

        # Consume credits
        user.ai_credits_used += amount
        await self.session.commit()

        logger.info(
            f"User {user_id} consumed {amount} AI credit(s). "
            f"Now {user.ai_credits_used}/{user.ai_credits_limit}"
        )

        return user.ai_credits_used

    async def get_credits_info(self, user_id: UUID) -> dict:
        """
        Get credits info for a user.

        Returns dict with:
            - plan: User's current plan
            - credits_used: Credits used this period
            - credits_limit: Total credits for plan
            - credits_remaining: Credits remaining
            - resets_at: When credits reset
            - is_unlimited: True if admin with unlimited credits
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Calculate reset date based on subscription or rolling period
        if user.stripe_subscription_id and user.plan_expires_at:
            # For subscriptions, credits reset at billing period end
            next_reset = user.plan_expires_at
        elif user.ai_credits_reset_at:
            # For free users, rolling 30-day reset
            next_reset = user.ai_credits_reset_at + timedelta(days=30)
        else:
            # If no reset date, set to end of current month
            now = datetime.now(timezone.utc)
            next_reset = (now.replace(day=1) + timedelta(days=32)).replace(day=1)

        return {
            "plan": user.plan.value,
            "credits_used": user.ai_credits_used,
            "credits_limit": user.ai_credits_limit,
            "credits_remaining": user.ai_credits_remaining,
            "resets_at": next_reset.isoformat(),
            "is_unlimited": user.is_admin,
        }

    async def reset_credits(self, user_id: UUID) -> None:
        """
        Manually reset a user's credits (admin function).
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        user.ai_credits_used = 0
        user.ai_credits_reset_at = datetime.now(timezone.utc)
        await self.session.commit()

        logger.info(f"Reset AI credits for user {user_id}")

    async def _maybe_reset_credits(self, user: User) -> None:
        """
        Reset credits if billing period has elapsed.

        For Stripe subscribers: Credits reset via webhook on invoice.paid
        For free users: Credits reset 30 days after the last reset
        """
        now = datetime.now(timezone.utc)

        # If no reset date, set it now (new user or first check)
        if user.ai_credits_reset_at is None:
            user.ai_credits_reset_at = now
            await self.session.commit()
            return

        # For subscribers, credits are reset by Stripe webhook (invoice.paid)
        # Only do lazy reset for non-subscribers (free users)
        if user.stripe_subscription_id:
            # Subscriber - don't auto-reset, wait for webhook
            # But check if subscription has lapsed
            if user.plan_expires_at and now > user.plan_expires_at:
                # Subscription period ended but no renewal webhook received
                # This could mean the subscription was cancelled
                logger.warning(
                    f"User {user.id} subscription period ended but no renewal. "
                    f"Keeping current credits until subscription status is confirmed."
                )
            return

        # Free user - 30 day rolling reset
        days_since_reset = (now - user.ai_credits_reset_at).days
        if days_since_reset >= 30:
            user.ai_credits_used = 0
            user.ai_credits_reset_at = now
            await self.session.commit()
            logger.info(f"Auto-reset AI credits for free user {user.id}")


# Convenience functions for use outside of class context

async def check_ai_credits(session: AsyncSession, user_id: UUID) -> bool:
    """Check if user has AI credits available."""
    service = AICreditsService(session)
    return await service.check_credits(user_id)


async def consume_ai_credit(
    session: AsyncSession,
    user_id: UUID,
    amount: int = 1,
) -> int:
    """Consume AI credits for a user."""
    service = AICreditsService(session)
    return await service.consume_credit(user_id, amount)


async def get_user_credits_info(session: AsyncSession, user_id: UUID) -> dict:
    """Get credits info for a user."""
    service = AICreditsService(session)
    return await service.get_credits_info(user_id)


async def reset_user_credits(session: AsyncSession, user_id: UUID) -> None:
    """Reset credits for a user."""
    service = AICreditsService(session)
    await service.reset_credits(user_id)
