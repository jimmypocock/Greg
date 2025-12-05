"""
AI cost tracking service.

Logs individual requests and maintains daily aggregates.
"""

import logging
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import AICostDaily, AIRequest, LLMProvider, RequestType
from src.costs.pricing import calculate_cost

logger = logging.getLogger(__name__)


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

    # Update daily aggregate
    await update_daily_aggregate(
        session=session,
        user_id=user_id,
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        input_cost=input_cost,
        output_cost=output_cost,
        total_cost=total_cost,
        latency_ms=latency_ms,
        success=success,
    )

    await session.commit()

    logger.info(
        f"Logged AI request: user={user_id}, model={model}, "
        f"tokens={input_tokens}+{output_tokens}, cost=${total_cost:.6f}"
    )

    return request


async def update_daily_aggregate(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    provider: LLMProvider,
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int,
    input_cost: Decimal,
    output_cost: Decimal,
    total_cost: Decimal,
    latency_ms: int | None,
    success: bool,
) -> AICostDaily:
    """
    Update or create daily aggregate record.

    Uses upsert pattern to atomically update the aggregate.
    """
    today = date.today()

    # Try to find existing record
    stmt = select(AICostDaily).where(
        AICostDaily.user_id == user_id,
        AICostDaily.date == today,
        AICostDaily.provider == provider,
        AICostDaily.model == model,
    )
    result = await session.execute(stmt)
    daily = result.scalar_one_or_none()

    if daily is None:
        # Create new record
        daily = AICostDaily(
            user_id=user_id,
            date=today,
            provider=provider,
            model=model,
            total_requests=1,
            successful_requests=1 if success else 0,
            failed_requests=0 if success else 1,
            total_input_tokens=input_tokens,
            total_output_tokens=output_tokens,
            total_cached_tokens=cached_tokens,
            total_input_cost_usd=input_cost,
            total_output_cost_usd=output_cost,
            total_cost_usd=total_cost,
            avg_latency_ms=latency_ms,
        )
        session.add(daily)
    else:
        # Update existing record
        daily.total_requests += 1
        if success:
            daily.successful_requests += 1
        else:
            daily.failed_requests += 1

        daily.total_input_tokens += input_tokens
        daily.total_output_tokens += output_tokens
        daily.total_cached_tokens += cached_tokens
        daily.total_input_cost_usd += input_cost
        daily.total_output_cost_usd += output_cost
        daily.total_cost_usd += total_cost

        # Update average latency
        if latency_ms is not None:
            if daily.avg_latency_ms is None:
                daily.avg_latency_ms = latency_ms
            else:
                # Running average
                n = daily.total_requests
                daily.avg_latency_ms = int(
                    (daily.avg_latency_ms * (n - 1) + latency_ms) / n
                )

    return daily


async def get_user_daily_costs(
    session: AsyncSession,
    user_id: uuid.UUID,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[AICostDaily]:
    """
    Get daily cost aggregates for a user.

    Args:
        session: Database session
        user_id: User ID
        start_date: Start date (defaults to 30 days ago)
        end_date: End date (defaults to today)

    Returns:
        List of daily cost records.
    """
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        from datetime import timedelta
        start_date = end_date - timedelta(days=30)

    stmt = (
        select(AICostDaily)
        .where(
            AICostDaily.user_id == user_id,
            AICostDaily.date >= start_date,
            AICostDaily.date <= end_date,
        )
        .order_by(AICostDaily.date.desc())
    )

    result = await session.execute(stmt)
    return list(result.scalars().all())


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
        start_date: Start date
        end_date: End date

    Returns:
        Total cost in USD.
    """
    from sqlalchemy import func

    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date  # Just today

    stmt = select(func.sum(AICostDaily.total_cost_usd)).where(
        AICostDaily.user_id == user_id,
        AICostDaily.date >= start_date,
        AICostDaily.date <= end_date,
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
