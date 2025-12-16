"""
AI cost tracking service.

Logs individual requests and computes aggregates on-the-fly from ai_requests.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database.models import AIRequest, LLMProvider, RequestType

logger = logging.getLogger(__name__)


@dataclass
class DailyCostSummary:
    """Aggregated cost summary for a specific day/provider/model."""

    date: date
    provider: LLMProvider
    model: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_input_tokens: int
    total_output_tokens: int
    total_cached_tokens: int
    total_input_cost_usd: Decimal
    total_output_cost_usd: Decimal
    total_cost_usd: Decimal
    avg_latency_ms: int | None


def get_provider_from_model(model: str) -> LLMProvider:
    """
    Determine the provider from the model name.

    Args:
        model: Model name

    Returns:
        LLMProvider enum value
    """
    model_lower = model.lower()

    if model_lower.startswith(("gpt-", "o1-", "text-", "davinci", "curie", "babbage", "ada")):
        return LLMProvider.OPENAI
    elif model_lower.startswith(("claude-",)):
        return LLMProvider.ANTHROPIC
    elif model_lower.startswith(("gemini-",)):
        return LLMProvider.GOOGLE
    else:
        # Default to Ollama for unknown models (local)
        return LLMProvider.OLLAMA


async def log_request(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    request_type: RequestType,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
    latency_ms: int | None = None,
    success: bool = True,
    error_message: str | None = None,
    provider: LLMProvider | None = None,
) -> AIRequest:
    """
    Log an individual AI request.

    Args:
        session: Database session
        user_id: User who made the request
        request_type: Type of request (chat, search)
        model: Model name used
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cached_tokens: Number of cached input tokens
        latency_ms: Request latency in milliseconds
        success: Whether the request succeeded
        error_message: Error message if failed
        provider: LLM provider (auto-detected if not provided)

    Returns:
        The created AIRequest record.
    """
    from packages.core.costs.pricing import calculate_cost

    # Auto-detect provider if not specified
    if provider is None:
        provider = get_provider_from_model(model)

    # Calculate costs
    input_cost, output_cost, total_cost = calculate_cost(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
    )

    # Create request record
    request = AIRequest(
        user_id=user_id,
        request_type=request_type,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        input_cost_usd=input_cost,
        output_cost_usd=output_cost,
        total_cost_usd=total_cost,
        latency_ms=latency_ms,
        success=success,
        error_message=error_message,
    )

    session.add(request)
    await session.commit()

    logger.info(
        f"Logged AI request: user={user_id}, model={model}, "
        f"tokens={input_tokens}+{output_tokens}, cost=${total_cost:.6f}"
    )

    return request


async def get_user_daily_costs(
    session: AsyncSession,
    user_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[DailyCostSummary]:
    """
    Get daily cost aggregates for a user.

    Aggregates are computed on-the-fly from ai_requests.

    Args:
        session: Database session
        user_id: User ID
        start_date: Start date (defaults to 30 days ago)
        end_date: End date (defaults to today)

    Returns:
        List of daily cost summaries.
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    # Aggregate by date, provider, model
    stmt = (
        select(
            func.date(AIRequest.created_at).label("date"),
            AIRequest.provider,
            AIRequest.model,
            func.count().label("total_requests"),
            func.sum(func.cast(AIRequest.success, Integer)).label("successful_requests"),
            func.sum(AIRequest.input_tokens).label("total_input_tokens"),
            func.sum(AIRequest.output_tokens).label("total_output_tokens"),
            func.sum(AIRequest.cached_tokens).label("total_cached_tokens"),
            func.sum(AIRequest.input_cost_usd).label("total_input_cost_usd"),
            func.sum(AIRequest.output_cost_usd).label("total_output_cost_usd"),
            func.sum(AIRequest.total_cost_usd).label("total_cost_usd"),
            func.avg(AIRequest.latency_ms).label("avg_latency_ms"),
        )
        .where(
            AIRequest.user_id == user_id,
            func.date(AIRequest.created_at) >= start_date,
            func.date(AIRequest.created_at) <= end_date,
        )
        .group_by(
            func.date(AIRequest.created_at),
            AIRequest.provider,
            AIRequest.model,
        )
        .order_by(func.date(AIRequest.created_at).desc())
    )

    result = await session.execute(stmt)
    rows = result.all()

    summaries = []
    for row in rows:
        total = row.total_requests
        successful = row.successful_requests or 0
        summaries.append(
            DailyCostSummary(
                date=row.date,
                provider=row.provider,
                model=row.model,
                total_requests=total,
                successful_requests=successful,
                failed_requests=total - successful,
                total_input_tokens=row.total_input_tokens or 0,
                total_output_tokens=row.total_output_tokens or 0,
                total_cached_tokens=row.total_cached_tokens or 0,
                total_input_cost_usd=row.total_input_cost_usd or Decimal("0"),
                total_output_cost_usd=row.total_output_cost_usd or Decimal("0"),
                total_cost_usd=row.total_cost_usd or Decimal("0"),
                avg_latency_ms=int(row.avg_latency_ms) if row.avg_latency_ms else None,
            )
        )

    return summaries


async def get_user_total_cost(
    session: AsyncSession,
    user_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None,
) -> Decimal:
    """
    Get total cost for a user over a date range.

    Args:
        session: Database session
        user_id: User ID
        start_date: Start date (defaults to today)
        end_date: End date (defaults to today)

    Returns:
        Total cost in USD.
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date  # Just today

    stmt = select(func.sum(AIRequest.total_cost_usd)).where(
        AIRequest.user_id == user_id,
        func.date(AIRequest.created_at) >= start_date,
        func.date(AIRequest.created_at) <= end_date,
    )

    result = await session.execute(stmt)
    total = result.scalar_one_or_none()

    return total or Decimal("0")


async def get_recent_requests(
    session: AsyncSession,
    user_id: uuid.UUID,
    limit: int = 50,
) -> list[AIRequest]:
    """
    Get recent AI requests for a user.

    Args:
        session: Database session
        user_id: User ID
        limit: Maximum number of requests to return

    Returns:
        List of recent AI requests.
    """
    stmt = (
        select(AIRequest)
        .where(AIRequest.user_id == user_id)
        .order_by(AIRequest.created_at.desc())
        .limit(limit)
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_all_daily_costs(
    session: AsyncSession,
    start_date: date | None = None,
    end_date: date | None = None,
    user_id: uuid.UUID | None = None,
) -> list[DailyCostSummary]:
    """
    Get daily cost aggregates for all users (admin).

    Args:
        session: Database session
        start_date: Start date (defaults to 30 days ago)
        end_date: End date (defaults to today)
        user_id: Optional user ID to filter by

    Returns:
        List of daily cost summaries.
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=30)

    # Aggregate by date, provider, model
    stmt = (
        select(
            func.date(AIRequest.created_at).label("date"),
            AIRequest.provider,
            AIRequest.model,
            func.count().label("total_requests"),
            func.sum(func.cast(AIRequest.success, Integer)).label("successful_requests"),
            func.sum(AIRequest.input_tokens).label("total_input_tokens"),
            func.sum(AIRequest.output_tokens).label("total_output_tokens"),
            func.sum(AIRequest.cached_tokens).label("total_cached_tokens"),
            func.sum(AIRequest.input_cost_usd).label("total_input_cost_usd"),
            func.sum(AIRequest.output_cost_usd).label("total_output_cost_usd"),
            func.sum(AIRequest.total_cost_usd).label("total_cost_usd"),
            func.avg(AIRequest.latency_ms).label("avg_latency_ms"),
        )
        .where(
            func.date(AIRequest.created_at) >= start_date,
            func.date(AIRequest.created_at) <= end_date,
        )
    )

    # Optional user filter
    if user_id is not None:
        stmt = stmt.where(AIRequest.user_id == user_id)

    stmt = stmt.group_by(
        func.date(AIRequest.created_at),
        AIRequest.provider,
        AIRequest.model,
    ).order_by(func.date(AIRequest.created_at).desc())

    result = await session.execute(stmt)
    rows = result.all()

    summaries = []
    for row in rows:
        total = row.total_requests
        successful = row.successful_requests or 0
        summaries.append(
            DailyCostSummary(
                date=row.date,
                provider=row.provider,
                model=row.model,
                total_requests=total,
                successful_requests=successful,
                failed_requests=total - successful,
                total_input_tokens=row.total_input_tokens or 0,
                total_output_tokens=row.total_output_tokens or 0,
                total_cached_tokens=row.total_cached_tokens or 0,
                total_input_cost_usd=row.total_input_cost_usd or Decimal("0"),
                total_output_cost_usd=row.total_output_cost_usd or Decimal("0"),
                total_cost_usd=row.total_cost_usd or Decimal("0"),
                avg_latency_ms=int(row.avg_latency_ms) if row.avg_latency_ms else None,
            )
        )

    return summaries
