"""
FastAPI dependencies for billing and credits.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import CurrentUser
from api.billing.credits import AICreditsService, InsufficientCreditsError
from api.database import get_session_dependency


async def get_credits_service(
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
) -> AICreditsService:
    """Get AI credits service instance."""
    return AICreditsService(session)


class RequireAICredits:
    """
    Dependency that checks and consumes AI credits.

    Usage:
        @router.post("/ai/generate")
        async def generate(
            user: CurrentUser,
            _credits: Annotated[None, Depends(RequireAICredits())],
        ):
            # User has credits, proceed with AI call
            ...

    Or with custom amount:
        _credits: Annotated[None, Depends(RequireAICredits(amount=2))]
    """

    def __init__(self, amount: int = 1, consume: bool = True):
        """
        Args:
            amount: Number of credits required (default 1)
            consume: Whether to consume credits (default True).
                     Set to False to just check without consuming.
        """
        self.amount = amount
        self.consume = consume

    async def __call__(
        self,
        user: CurrentUser,
        session: Annotated[AsyncSession, Depends(get_session_dependency)],
    ) -> None:
        """Check and optionally consume AI credits."""
        service = AICreditsService(session)

        try:
            if self.consume:
                await service.consume_credit(user.id, self.amount)
            else:
                await service.check_credits(user.id)
        except InsufficientCreditsError as e:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail={
                    "error": "insufficient_credits",
                    "message": e.message,
                    "credits_used": e.credits_used,
                    "credits_limit": e.credits_limit,
                    "plan": e.plan.value,
                    "upgrade_url": "/settings/billing",  # Frontend route
                },
            )
