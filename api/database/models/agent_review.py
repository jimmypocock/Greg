"""
AgentReview model.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from api.database.models.base import Base
from api.enums import AgentTaskType, AgentType


class AgentReview(Base):
    """A review/feedback from an AI agent. Immutable - no updated_at."""

    __tablename__ = "agent_reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    song_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("songs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Agent info
    agent_type: Mapped[AgentType] = mapped_column(
        Enum(AgentType, name="agenttype", create_type=False),
        nullable=False,
    )
    task_type: Mapped[AgentTaskType] = mapped_column(
        Enum(AgentTaskType, name="agenttasktype", create_type=False),
        nullable=False,
    )

    # The actual review content
    result: Mapped[str] = mapped_column(Text, nullable=False)

    # Cost tracking
    input_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    output_tokens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_cost_usd: Mapped[Decimal] = mapped_column(
        Numeric(precision=10, scale=6),
        default=Decimal("0"),
        nullable=False,
    )

    # Performance
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Status
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamp (no updated_at - reviews are immutable)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"<AgentReview {self.agent_type.value}/{self.task_type.value} {status}>"
