"""
Pydantic schemas for cost tracking.

Defines request/response schemas for cost endpoints.
"""

from pydantic import BaseModel


# Schemas


class DailyCostResponse(BaseModel):
    """Daily cost summary response."""

    avg_latency_ms: int | None
    date: str
    failed_requests: int
    model: str
    provider: str
    successful_requests: int
    total_cached_tokens: int
    total_cost_usd: str
    total_input_cost_usd: str
    total_input_tokens: int
    total_output_cost_usd: str
    total_output_tokens: int
    total_requests: int


class RequestLogResponse(BaseModel):
    """AI request log response."""

    cached_tokens: int
    created_at: str
    error_message: str | None
    id: str
    input_cost_usd: str
    input_tokens: int
    latency_ms: int | None
    model: str
    output_cost_usd: str
    output_tokens: int
    provider: str
    request_type: str
    success: bool
    total_cost_usd: str


class CostSummaryResponse(BaseModel):
    """Cost summary response."""

    daily_breakdown: list[DailyCostResponse]
    period_end: str
    period_start: str
    total_cost_usd: str
    total_requests: int
    requests: list[RequestLogResponse] | None = None
