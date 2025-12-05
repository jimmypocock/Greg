"""
AI cost tracking routes.

Endpoints:
    GET /costs           - Get user's daily cost summary
    GET /costs/requests  - Get recent AI requests
    GET /costs/total     - Get total cost for a period
"""

import logging
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import CurrentUser, AdminUser
from src.database import get_session_dependency, User
from src.costs import get_user_daily_costs, get_user_total_cost, get_recent_requests

logger = logging.getLogger(__name__)

router = APIRouter()


class DailyCostResponse(BaseModel):
    """Daily cost summary response."""

    date: str
    provider: str
    model: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cached_tokens: int
    total_input_cost_usd: str
    total_output_cost_usd: str
    total_cost_usd: str
    avg_latency_ms: int | None


class CostSummaryResponse(BaseModel):
    """Cost summary response."""

    period_start: str
    period_end: str
    total_cost_usd: str
    total_requests: int
    daily_breakdown: list[DailyCostResponse]


class RequestLogResponse(BaseModel):
    """AI request log response."""

    id: str
    request_type: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    input_cost_usd: str
    output_cost_usd: str
    total_cost_usd: str
    latency_ms: int | None
    success: bool
    error_message: str | None
    created_at: str


class TotalCostResponse(BaseModel):
    """Total cost response."""

    period_start: str
    period_end: str
    total_cost_usd: str


@router.get("/costs", response_model=CostSummaryResponse)
async def get_costs(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
):
    """
    Get daily cost summary for the current user.

    Args:
        days: Number of days to include (default: 30)
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    # Get daily costs
    daily_costs = await get_user_daily_costs(
        session=session,
        user_id=user.id,
        start_date=start_date,
        end_date=end_date,
    )

    # Calculate totals
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


@router.get("/costs/requests", response_model=list[RequestLogResponse])
async def get_requests(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
):
    """
    Get recent AI requests for the current user.

    Args:
        limit: Maximum number of requests to return (default: 50)
    """
    requests = await get_recent_requests(
        session=session,
        user_id=user.id,
        limit=limit,
    )

    return [
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
        for r in requests
    ]


@router.get("/costs/total", response_model=TotalCostResponse)
async def get_total_cost(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
):
    """
    Get total cost for a period.

    Args:
        days: Number of days to include (default: 30)
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    total = await get_user_total_cost(
        session=session,
        user_id=user.id,
        start_date=start_date,
        end_date=end_date,
    )

    return TotalCostResponse(
        period_start=start_date.isoformat(),
        period_end=end_date.isoformat(),
        total_cost_usd=str(total),
    )
