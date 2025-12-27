"""
AI Request model for per-request logging and cost tracking.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from enum import Enum as PyEnum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from api.database.models.user import User


class LLMProvider(str, PyEnum):
    """LLM provider names."""

    OLLAMA = "ollama"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"


class RequestType(str, PyEnum):
    """Type of AI request."""

    CHAT = "chat"
    SEARCH = "search"


class AIRequest(Base, TimestampMixin):
    """Individual AI request log for cost tracking and analytics."""

    __tablename__ = "ai_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    request_type: Mapped[RequestType] = mapped_column(
        Enum(RequestType),
        nullable=False,
    )
    provider: Mapped[LLMProvider] = mapped_column(
        Enum(LLMProvider),
        nullable=False,
        index=True,
    )
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    # Token counts
    input_tokens: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )
    output_tokens: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )
    cached_tokens: Mapped[int] = mapped_column(
        BigInteger,
        default=0,
        nullable=False,
    )

    # Cost breakdown (precision: 6 decimal places for fractional cents)
    input_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        default=Decimal("0"),
        nullable=False,
    )
    output_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        default=Decimal("0"),
        nullable=False,
    )
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(10, 6),
        default=Decimal("0"),
        nullable=False,
    )

    # Performance
    latency_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    # Status
    success: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
