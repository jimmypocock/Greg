"""
Billing and credits routes for the Songwriter app.

Endpoints:
    GET  /billing/credits         - Get current user's credits info
    GET  /billing/plans           - Get available plans and pricing
    POST /billing/checkout        - Create Stripe checkout session
    POST /billing/portal          - Create Stripe customer portal session
    POST /billing/cancel          - Cancel subscription at period end
    GET  /billing/subscription    - Get current subscription status
    GET  /billing/referral-code   - Get user's referral code
    GET  /billing/referral-stats  - Get referral statistics
"""

import logging
import secrets
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import CurrentUser
from api.billing import AICreditsService, StripeConfigError, StripeService, is_stripe_configured
from api.config import Config
from api.database import get_session_dependency
from api.database.models import PLAN_CREDITS, Invite, InviteType, User, UserPlan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


class CreditsInfoResponse(BaseModel):
    """User's current credits information."""

    plan: str
    credits_used: int
    credits_limit: int
    credits_remaining: int
    resets_at: str
    is_unlimited: bool


class PlanInfo(BaseModel):
    """Information about a subscription plan."""

    id: str
    name: str
    price_monthly: int  # In cents
    credits_per_month: int
    features: list[str]


class PlansResponse(BaseModel):
    """Available subscription plans."""

    plans: list[PlanInfo]


# Plan definitions
PLANS = [
    PlanInfo(
        id="free",
        name="Free",
        price_monthly=0,
        credits_per_month=PLAN_CREDITS[UserPlan.FREE],
        features=[
            "Basic song editing",
            f"{PLAN_CREDITS[UserPlan.FREE]} AI credits/month",
            "Single user",
        ],
    ),
    PlanInfo(
        id="pro",
        name="Pro",
        price_monthly=1000,  # $10.00
        credits_per_month=PLAN_CREDITS[UserPlan.PRO],
        features=[
            "Everything in Free",
            f"{PLAN_CREDITS[UserPlan.PRO]} AI credits/month",
            "Real-time collaboration",
            "Share links",
            "Priority support",
        ],
    ),
    PlanInfo(
        id="enterprise",
        name="Enterprise",
        price_monthly=2500,  # $25.00
        credits_per_month=PLAN_CREDITS[UserPlan.ENTERPRISE],
        features=[
            "Everything in Pro",
            f"{PLAN_CREDITS[UserPlan.ENTERPRISE]} AI credits/month",
            "Team workspaces",
            "Advanced analytics",
            "Dedicated support",
        ],
    ),
]


@router.get("/credits", response_model=CreditsInfoResponse)
async def get_credits_info(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Get the current user's AI credits information.

    Returns:
        - Current plan
        - Credits used this billing period
        - Total credits available
        - Credits remaining
        - When credits reset
        - Whether user has unlimited credits (admin)
    """
    service = AICreditsService(session)
    info = await service.get_credits_info(user.id)

    return CreditsInfoResponse(
        plan=info["plan"],
        credits_used=info["credits_used"],
        credits_limit=info["credits_limit"],
        credits_remaining=info["credits_remaining"],
        resets_at=info["resets_at"],
        is_unlimited=info["is_unlimited"],
    )


@router.get("/plans", response_model=PlansResponse)
async def get_plans():
    """
    Get available subscription plans.

    Returns list of plans with pricing and features.
    """
    return PlansResponse(plans=PLANS)


# Stripe subscription endpoints


class CheckoutRequest(BaseModel):
    """Request to create a checkout session."""

    success_url: str = Field(..., description="URL to redirect after successful payment")
    cancel_url: str = Field(..., description="URL to redirect if user cancels")
    plan: str = Field(default="pro", description="Plan to subscribe to (pro or enterprise)")


class CheckoutResponse(BaseModel):
    """Response with checkout session URL."""

    checkout_url: str = Field(..., description="Stripe checkout URL to redirect user to")


class PortalRequest(BaseModel):
    """Request to create a customer portal session."""

    return_url: str = Field(..., description="URL to return to after portal session")


class PortalResponse(BaseModel):
    """Response with customer portal URL."""

    portal_url: str = Field(..., description="Stripe customer portal URL")


class SubscriptionResponse(BaseModel):
    """Current subscription status."""

    has_subscription: bool
    status: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False
    plan: Optional[dict] = None


class CancelResponse(BaseModel):
    """Response after cancelling subscription."""

    cancelled: bool
    message: str


def _get_price_id_for_plan(plan: str) -> str:
    """Get Stripe price ID for a plan."""
    if plan == "pro":
        if not Config.STRIPE_PRICE_ID_PRO:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Pro plan price not configured. Set STRIPE_PRICE_ID_PRO in environment.",
            )
        return Config.STRIPE_PRICE_ID_PRO
    elif plan == "enterprise":
        # Enterprise has its own price ID
        if not Config.STRIPE_PRICE_ID_ENTERPRISE:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Enterprise plan not available for self-service signup.",
            )
        return Config.STRIPE_PRICE_ID_ENTERPRISE
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown plan: {plan}. Available: pro, enterprise",
        )


@router.post("/checkout", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CheckoutRequest,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Create a Stripe checkout session for subscription.

    Redirects user to Stripe-hosted checkout page.
    After payment, user is redirected to success_url.
    """
    if not is_stripe_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payments not configured. Contact support.",
        )

    price_id = _get_price_id_for_plan(request.plan)

    try:
        stripe_service = StripeService(session)
        checkout_url = await stripe_service.create_checkout_session(
            user_id=user.id,
            price_id=price_id,
            success_url=request.success_url,
            cancel_url=request.cancel_url,
        )
        return CheckoutResponse(checkout_url=checkout_url)
    except StripeConfigError as e:
        logger.error(f"Stripe config error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payments not properly configured.",
        )
    except Exception as e:
        logger.error(f"Error creating checkout session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create checkout session.",
        )


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(
    request: PortalRequest,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Create a Stripe customer portal session.

    The portal allows users to:
    - Update payment methods
    - View invoices and billing history
    - Cancel subscription
    - Download receipts
    """
    if not is_stripe_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payments not configured.",
        )

    try:
        stripe_service = StripeService(session)
        portal_url = await stripe_service.create_portal_session(
            user_id=user.id,
            return_url=request.return_url,
        )
        return PortalResponse(portal_url=portal_url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except StripeConfigError as e:
        logger.error(f"Stripe config error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payments not properly configured.",
        )
    except Exception as e:
        logger.error(f"Error creating portal session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create portal session.",
        )


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription_status(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Get current subscription status.

    Returns subscription details if user has an active subscription.
    """
    if not is_stripe_configured():
        return SubscriptionResponse(
            has_subscription=False,
            status=None,
            cancel_at_period_end=False,
        )

    try:
        stripe_service = StripeService(session)
        subscription = await stripe_service.get_subscription_status(user.id)

        if not subscription:
            return SubscriptionResponse(
                has_subscription=False,
                status=None,
                cancel_at_period_end=False,
            )

        return SubscriptionResponse(
            has_subscription=True,
            status=subscription["status"],
            current_period_end=subscription["current_period_end"],
            cancel_at_period_end=subscription["cancel_at_period_end"],
            plan=subscription["plan"],
        )
    except StripeConfigError:
        return SubscriptionResponse(
            has_subscription=False,
            status=None,
            cancel_at_period_end=False,
        )
    except Exception as e:
        logger.error(f"Error getting subscription status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get subscription status.",
        )


@router.post("/cancel", response_model=CancelResponse)
async def cancel_subscription(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Cancel subscription at end of billing period.

    User retains access until current period ends.
    """
    if not is_stripe_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payments not configured.",
        )

    try:
        stripe_service = StripeService(session)
        cancelled = await stripe_service.cancel_subscription(user.id)

        if cancelled:
            return CancelResponse(
                cancelled=True,
                message="Subscription will be cancelled at end of billing period. "
                        "You'll retain access until then.",
            )
        else:
            return CancelResponse(
                cancelled=False,
                message="No active subscription found to cancel.",
            )
    except StripeConfigError as e:
        logger.error(f"Stripe config error: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payments not properly configured.",
        )
    except Exception as e:
        logger.error(f"Error cancelling subscription: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel subscription.",
        )


# Referral endpoints

REFERRAL_CREDITS_REWARD = 5  # Credits referrer earns per signup


class ReferralCodeResponse(BaseModel):
    """User's referral code."""

    code: str
    url: str


class ReferralStatsResponse(BaseModel):
    """User's referral statistics."""

    referral_count: int
    credits_earned: int
    pending_referrals: int = 0


@router.get("/referral-code", response_model=ReferralCodeResponse)
async def get_referral_code(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Get the current user's referral code.

    Creates one if it doesn't exist.
    """
    # Check if user already has a referral invite
    result = await session.execute(
        select(Invite).where(
            Invite.created_by == user.id,
            Invite.type == InviteType.REFERRAL,
        )
    )
    invite = result.scalar_one_or_none()

    if not invite:
        # Create a new referral invite for this user
        code = secrets.token_urlsafe(8)  # 11 char code
        invite = Invite(
            code=code,
            type=InviteType.REFERRAL,
            created_by=user.id,
            referrer_credits=REFERRAL_CREDITS_REWARD,
            max_uses=None,  # Unlimited
            is_active=True,
        )
        session.add(invite)
        await session.commit()
        await session.refresh(invite)
        logger.info(f"Created referral code {code} for user {user.email}")

    # Build referral URL
    base_url = Config.FRONTEND_URL or "http://localhost:3000"
    referral_url = f"{base_url}/register?ref={invite.code}"

    return ReferralCodeResponse(
        code=invite.code,
        url=referral_url,
    )


@router.get("/referral-stats", response_model=ReferralStatsResponse)
async def get_referral_stats(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Get referral statistics for the current user.

    Returns:
        - referral_count: Number of users who signed up with user's code
        - credits_earned: Total credits earned from referrals
    """
    # Get user's referral invite
    result = await session.execute(
        select(Invite).where(
            Invite.created_by == user.id,
            Invite.type == InviteType.REFERRAL,
        )
    )
    invite = result.scalar_one_or_none()

    if not invite:
        return ReferralStatsResponse(
            referral_count=0,
            credits_earned=0,
        )

    # Count referred users
    referral_count = invite.use_count
    credits_earned = referral_count * invite.referrer_credits

    return ReferralStatsResponse(
        referral_count=referral_count,
        credits_earned=credits_earned,
    )
