"""
Webhook routes for external service integrations.

Endpoints:
    POST /webhooks/stripe - Handle Stripe webhook events
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.billing import StripeConfigError, StripeService, is_stripe_configured
from packages.core.database import get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


class WebhookResponse(BaseModel):
    """Response for webhook processing."""

    received: bool
    event_type: str | None = None
    status: str


@router.post("/stripe", response_model=WebhookResponse)
async def stripe_webhook(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
    stripe_signature: str = Header(None, alias="Stripe-Signature"),
):
    """
    Handle Stripe webhook events.

    This endpoint receives events from Stripe for:
    - checkout.session.completed - New subscription created
    - invoice.paid - Subscription renewed (credits reset here)
    - customer.subscription.deleted - Subscription cancelled
    - customer.subscription.updated - Subscription modified
    - invoice.payment_failed - Payment failed

    IMPORTANT: This endpoint must be publicly accessible for Stripe.
    Configure your webhook in Stripe Dashboard to point to:
    https://your-domain.com/webhooks/stripe
    """
    if not is_stripe_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe not configured",
        )

    if not stripe_signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )

    # Get raw body for signature verification
    payload = await request.body()

    try:
        stripe_service = StripeService(session)
        result = await stripe_service.process_webhook(payload, stripe_signature)

        return WebhookResponse(
            received=True,
            event_type=result["event_type"],
            status=result["status"],
        )

    except ValueError as e:
        # Invalid signature
        logger.warning(f"Invalid Stripe webhook signature: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    except StripeConfigError as e:
        logger.error(f"Stripe config error in webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe not properly configured",
        )

    except Exception as e:
        # Log but don't expose internal errors
        logger.error(f"Error processing Stripe webhook: {e}", exc_info=True)
        # Return 200 to prevent Stripe from retrying
        # (we log the error and can investigate later)
        return WebhookResponse(
            received=True,
            event_type=None,
            status="error",
        )
