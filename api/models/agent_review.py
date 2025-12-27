"""AgentReview model (SQLModel - works for API + DB)."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, Enum, text
from sqlmodel import Field, SQLModel

from api.enums import AgentTaskType, AgentType
from api.models.utils import utc_now


class AgentReview(SQLModel, table=True):
    """A review/feedback from an AI agent."""

    __tablename__ = "agent_reviews"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    song_id: uuid.UUID = Field(foreign_key="songs.id", index=True)

    # Agent info
    agent_type: AgentType = Field(
        sa_column=Column(
            Enum(AgentType, name="agenttype", create_type=False),
            nullable=False,
        ),
    )
    task_type: AgentTaskType = Field(
        sa_column=Column(
            Enum(AgentTaskType, name="agenttasktype", create_type=False),
            nullable=False,
        ),
    )

    # The actual review content
    result: str

    # Cost tracking
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    total_cost_usd: Decimal = Field(default=Decimal("0"))

    # Performance
    duration_ms: Optional[int] = None
    model: Optional[str] = Field(default=None, max_length=100)

    # Status
    success: bool = Field(default=True)
    error_message: Optional[str] = None

    # Timestamp
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column_kwargs={"server_default": text("now()")},
    )
