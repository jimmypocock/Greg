"""
Stripe integration service.

Handles customer creation, checkout sessions, subscriptions, and webhooks.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

import stripe
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import Config
from api.database.models import User, UserPlan

logger = logging.getLogger(__name__)


class StripeConfigError(Exception):
    """Raised when Stripe is not properly configured."""

    pass


class StripeService:
    """
    Service for Stripe subscription management.

    Handles:
    - Customer creation/retrieval
    - Checkout session creation for new subscriptions
    - Customer portal sessions for subscription management
    - Subscription status checks
    - Webhook event processing
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self._configure_stripe()

    def _configure_stripe(self) -> None:
        """Configure Stripe API key."""
        if not Config.STRIPE_SECRET_KEY:
            raise StripeConfigError(
                "STRIPE_SECRET_KEY is not configured. "
                "Set it in your .env file to enable payments."
            )
        stripe.api_key = Config.STRIPE_SECRET_KEY

    async def get_user(self, user_id: UUID) -> Optional[User]:
        """Get user by ID."""
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_user_by_stripe_customer(self, customer_id: str) -> Optional[User]:
        """Get user by Stripe customer ID."""
        result = await self.session.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_customer(self, user_id: UUID) -> str:
        """
        Get existing Stripe customer or create new one.

        Returns the Stripe customer ID.
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        # Return existing customer if present
        if user.stripe_customer_id:
            return user.stripe_customer_id

        # Create new Stripe customer
        customer = stripe.Customer.create(
            email=user.email,
            metadata={
                "user_id": str(user.id),
            },
        )

        # Save customer ID to user
        user.stripe_customer_id = customer.id
        await self.session.commit()

        logger.info(f"Created Stripe customer {customer.id} for user {user_id}")
        return customer.id

    async def create_checkout_session(
        self,
        user_id: UUID,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """
        Create a Stripe checkout session for subscription.

        Args:
            user_id: User ID
            price_id: Stripe Price ID for the plan
            success_url: URL to redirect after successful payment
            cancel_url: URL to redirect if user cancels

        Returns:
            Checkout session URL
        """
        customer_id = await self.get_or_create_customer(user_id)

        checkout_session = stripe.checkout.Session.create(
            customer=customer_id,
            mode="subscription",
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                "user_id": str(user_id),
            },
            subscription_data={
                "metadata": {
                    "user_id": str(user_id),
                }
            },
        )

        logger.info(f"Created checkout session {checkout_session.id} for user {user_id}")
        return checkout_session.url

    async def create_portal_session(
        self,
        user_id: UUID,
        return_url: str,
    ) -> str:
        """
        Create a Stripe customer portal session.

        The portal allows users to manage their subscription,
        update payment methods, view invoices, and cancel.

        Args:
            user_id: User ID
            return_url: URL to return to after portal session

        Returns:
            Portal session URL
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        if not user.stripe_customer_id:
            raise ValueError("User has no Stripe customer ID. Subscribe first.")

        portal_session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=return_url,
        )

        logger.info(f"Created portal session for user {user_id}")
        return portal_session.url

    async def cancel_subscription(self, user_id: UUID) -> bool:
        """
        Cancel user's subscription at end of billing period.

        Returns True if subscription was cancelled.
        """
        user = await self.get_user(user_id)
        if not user:
            raise ValueError(f"User {user_id} not found")

        if not user.stripe_subscription_id:
            return False

        # Cancel at period end (user keeps access until period ends)
        subscription = stripe.Subscription.modify(
            user.stripe_subscription_id,
            cancel_at_period_end=True,
        )

        logger.info(f"Scheduled subscription cancellation for user {user_id}")
        return subscription.cancel_at_period_end

    async def get_subscription_status(self, user_id: UUID) -> Optional[dict]:
        """
        Get current subscription status.

        Returns dict with:
            - status: active, trialing, past_due, canceled, etc.
            - current_period_end: When current period ends
            - cancel_at_period_end: Whether scheduled to cancel
            - plan: Plan details
        """
        user = await self.get_user(user_id)
        if not user or not user.stripe_subscription_id:
            return None

        try:
            subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)
            return {
                "status": subscription.status,
                "current_period_end": datetime.fromtimestamp(
                    subscription.current_period_end, tz=timezone.utc
                ).isoformat(),
                "cancel_at_period_end": subscription.cancel_at_period_end,
                "plan": {
                    "id": subscription["items"].data[0].price.id,
                    "product": subscription["items"].data[0].price.product,
                    "amount": subscription["items"].data[0].price.unit_amount,
                    "currency": subscription["items"].data[0].price.currency,
                    "interval": subscription["items"].data[0].price.recurring.interval,
                },
            }
        except stripe.StripeError as e:
            logger.error(f"Error retrieving subscription for user {user_id}: {e}")
            return None

    # Webhook event handlers

    async def handle_checkout_completed(self, event: dict) -> None:
        """
        Handle checkout.session.completed event.

        Called when a customer completes checkout and subscription is created.
        """
        session = event["data"]["object"]
        customer_id = session["customer"]
        subscription_id = session["subscription"]
        user_id_str = session.get("metadata", {}).get("user_id")

        if not user_id_str:
            logger.warning(f"No user_id in checkout session metadata: {session['id']}")
            return

        user = await self.get_user(UUID(user_id_str))
        if not user:
            logger.error(f"User {user_id_str} not found for checkout session")
            return

        # Get subscription details for period end
        subscription = stripe.Subscription.retrieve(subscription_id)

        # Update user with subscription info
        user.stripe_customer_id = customer_id
        user.stripe_subscription_id = subscription_id
        user.plan = UserPlan.PRO
        user.plan_started_at = datetime.fromtimestamp(
            subscription.current_period_start, tz=timezone.utc
        )
        user.plan_expires_at = datetime.fromtimestamp(
            subscription.current_period_end, tz=timezone.utc
        )
        # Reset credits for new subscription
        user.ai_credits_used = 0
        user.ai_credits_reset_at = datetime.now(timezone.utc)

        await self.session.commit()
        logger.info(f"User {user_id_str} upgraded to Pro plan")

    async def handle_invoice_paid(self, event: dict) -> None:
        """
        Handle invoice.paid event.

        Called when a subscription invoice is paid (including renewals).
        This is where we reset AI credits for the new billing period.
        """
        invoice = event["data"]["object"]
        customer_id = invoice["customer"]
        subscription_id = invoice.get("subscription")

        if not subscription_id:
            # One-time payment, not subscription
            return

        user = await self.get_user_by_stripe_customer(customer_id)
        if not user:
            logger.warning(f"No user found for customer {customer_id}")
            return

        # Get subscription for period dates
        subscription = stripe.Subscription.retrieve(subscription_id)

        # Update subscription dates
        user.plan_started_at = datetime.fromtimestamp(
            subscription.current_period_start, tz=timezone.utc
        )
        user.plan_expires_at = datetime.fromtimestamp(
            subscription.current_period_end, tz=timezone.utc
        )

        # Reset credits for new billing period
        user.ai_credits_used = 0
        user.ai_credits_reset_at = datetime.now(timezone.utc)

        await self.session.commit()
        logger.info(
            f"Reset AI credits for user {user.id} on invoice payment "
            f"(subscription {subscription_id})"
        )

    async def handle_subscription_deleted(self, event: dict) -> None:
        """
        Handle customer.subscription.deleted event.

        Called when a subscription is cancelled and period ends.
        Downgrades user to free plan.
        """
        subscription = event["data"]["object"]
        customer_id = subscription["customer"]

        user = await self.get_user_by_stripe_customer(customer_id)
        if not user:
            logger.warning(f"No user found for customer {customer_id}")
            return

        # Downgrade to free plan
        user.plan = UserPlan.FREE
        user.stripe_subscription_id = None
        user.plan_expires_at = None
        # Don't reset credits - they keep remaining credits until next natural reset

        await self.session.commit()
        logger.info(f"User {user.id} downgraded to Free plan")

    async def handle_subscription_updated(self, event: dict) -> None:
        """
        Handle customer.subscription.updated event.

        Called when subscription is modified (plan change, etc.)
        """
        subscription = event["data"]["object"]
        customer_id = subscription["customer"]

        user = await self.get_user_by_stripe_customer(customer_id)
        if not user:
            logger.warning(f"No user found for customer {customer_id}")
            return

        # Update subscription ID if changed
        user.stripe_subscription_id = subscription["id"]

        # Update period dates
        user.plan_started_at = datetime.fromtimestamp(
            subscription.current_period_start, tz=timezone.utc
        )
        user.plan_expires_at = datetime.fromtimestamp(
            subscription.current_period_end, tz=timezone.utc
        )

        # Check if subscription status changed
        if subscription["status"] in ("active", "trialing"):
            if user.plan == UserPlan.FREE:
                user.plan = UserPlan.PRO
                user.ai_credits_used = 0
                user.ai_credits_reset_at = datetime.now(timezone.utc)
        elif subscription["status"] in ("canceled", "unpaid"):
            user.plan = UserPlan.FREE
            user.stripe_subscription_id = None

        await self.session.commit()
        logger.info(f"Updated subscription for user {user.id}: {subscription['status']}")

    async def handle_payment_failed(self, event: dict) -> None:
        """
        Handle invoice.payment_failed event.

        Called when a payment attempt fails.
        Could be used to notify user or restrict access.
        """
        invoice = event["data"]["object"]
        customer_id = invoice["customer"]

        user = await self.get_user_by_stripe_customer(customer_id)
        if not user:
            return

        # For now just log - could add email notification here
        logger.warning(f"Payment failed for user {user.id}")

    async def process_webhook(self, payload: bytes, signature: str) -> dict:
        """
        Process incoming Stripe webhook.

        Args:
            payload: Raw request body
            signature: Stripe-Signature header value

        Returns:
            Dict with event type and status
        """
        if not Config.STRIPE_WEBHOOK_SECRET:
            raise StripeConfigError("STRIPE_WEBHOOK_SECRET is not configured")

        # Verify webhook signature
        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                Config.STRIPE_WEBHOOK_SECRET,
            )
        except stripe.SignatureVerificationError as e:
            logger.error(f"Invalid webhook signature: {e}")
            raise ValueError("Invalid webhook signature")

        event_type = event["type"]
        logger.info(f"Processing Stripe webhook: {event_type}")

        # Route to appropriate handler
        handlers = {
            "checkout.session.completed": self.handle_checkout_completed,
            "invoice.paid": self.handle_invoice_paid,
            "customer.subscription.deleted": self.handle_subscription_deleted,
            "customer.subscription.updated": self.handle_subscription_updated,
            "invoice.payment_failed": self.handle_payment_failed,
        }

        handler = handlers.get(event_type)
        if handler:
            await handler(event)
            return {"event_type": event_type, "status": "processed"}
        else:
            logger.debug(f"Unhandled webhook event type: {event_type}")
            return {"event_type": event_type, "status": "ignored"}


def is_stripe_configured() -> bool:
    """Check if Stripe is properly configured."""
    return bool(Config.STRIPE_SECRET_KEY)
