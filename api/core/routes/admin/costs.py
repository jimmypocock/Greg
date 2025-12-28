"""
Admin cost management routes.

Provides admin-only endpoints for viewing all users' costs.

Endpoints:
    GET /admin/costs - Get cost summary for all users or specific user
"""

from datetime import date, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import AdminUser
from api.costs import get_all_daily_costs
from api.costs.schemas import CostSummaryResponse, DailyCostResponse
from api.database import get_session_dependency

router = APIRouter()


# Routes


@router.get("", response_model=CostSummaryResponse)
async def get_admin_costs(
    admin: AdminUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    user_id: Annotated[UUID | None, Query()] = None,
):
    """
    Get cost summary for all users (admin only).

    Args:
        days: Number of days to include (default 30, max 365)
        user_id: Optional user ID to filter by specific user
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    daily_costs = await get_all_daily_costs(
        session=session,
        start_date=start_date,
        end_date=end_date,
        user_id=user_id,
    )

    total_cost = sum(d.total_cost_usd for d in daily_costs)
    total_requests = sum(d.total_requests for d in daily_costs)

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
    )
