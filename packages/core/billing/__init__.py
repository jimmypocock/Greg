"""
Billing and subscription management.

Handles AI credits, usage limits, and Stripe integration.
"""

from packages.core.billing.credits import (
    AICreditsService,
    InsufficientCreditsError,
    check_ai_credits,
    consume_ai_credit,
    get_user_credits_info,
    reset_user_credits,
)
from packages.core.billing.dependencies import (
    RequireAICredits,
    get_credits_service,
)
from packages.core.billing.stripe_service import (
    StripeConfigError,
    StripeService,
    is_stripe_configured,
)

__all__ = [
    # Service
    "AICreditsService",
    "StripeService",
    # Errors
    "InsufficientCreditsError",
    "StripeConfigError",
    # Functions
    "check_ai_credits",
    "consume_ai_credit",
    "get_user_credits_info",
    "reset_user_credits",
    "is_stripe_configured",
    # Dependencies
    "RequireAICredits",
    "get_credits_service",
]
