"""
AI cost tracking routes.

Provides cost tracking and usage statistics for AI requests.

Endpoints:
    GET /costs - Get user's cost summary with optional detail
"""

from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.auth import CurrentUser
from packages.core.costs import get_recent_requests, get_user_daily_costs
from packages.core.costs.schemas import (
    CostSummaryResponse,
    DailyCostResponse,
    RequestLogResponse,
)
from packages.core.database import get_session_dependency

router = APIRouter(tags=["Costs"])


# Routes


@router.get("/costs", response_model=CostSummaryResponse)
async def get_costs(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    detail: Annotated[bool, Query()] = False,
):
    """
    Get cost summary for the current user.

    Args:
        days: Number of days to include (default 30, max 365)
        detail: Include individual request logs
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    daily_costs = await get_user_daily_costs(
        session=session,
        user_id=user.id,
        start_date=start_date,
        end_date=end_date,
    )

    total_cost = sum(d.total_cost_usd for d in daily_costs)
    total_requests = sum(d.total_requests for d in daily_costs)

    requests = None
    if detail:
        request_logs = await get_recent_requests(
            session=session,
            user_id=user.id,
            limit=200,
        )
        requests = [
            RequestLogResponse(
                id=str(r.id),
                request_type=r.request_type.value,
                provider=r.provider.value,
                model=r.model,
                input_tokens=r.input_tokens,
                output_tokens=r.output_tokens,
                cached_tokens=r.cached_tokens,
                input_cost_usd=str(r.input_cost_usd),
                output_cost_usd=str(r.output_cost_usd),
                total_cost_usd=str(r.total_cost_usd),
                latency_ms=r.latency_ms,
                success=r.success,
                error_message=r.error_message,
                created_at=r.created_at.isoformat(),
            )
            for r in request_logs
        ]

    return CostSummaryResponse(
        period_start=start_date.isoformat(),
        period_end=end_date.isoformat(),
        total_cost_usd=str(total_cost),
        total_requests=total_requests,
        daily_breakdown=[
            DailyCostResponse(
                date=d.date.isoformat(),
                provider=d.provider.value,
                model=d.model,
                total_requests=d.total_requests,
                successful_requests=d.successful_requests,
                failed_requests=d.failed_requests,
                total_input_tokens=d.total_input_tokens,
                total_output_tokens=d.total_output_tokens,
                total_cached_tokens=d.total_cached_tokens,
                total_input_cost_usd=str(d.total_input_cost_usd),
                total_output_cost_usd=str(d.total_output_cost_usd),
                total_cost_usd=str(d.total_cost_usd),
                avg_latency_ms=d.avg_latency_ms,
            )
            for d in daily_costs
        ],
        requests=requests,
    )
