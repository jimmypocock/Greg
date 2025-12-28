"""ChatMessage model for persisting conversation history."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Column, DateTime, text
from sqlmodel import Field, SQLModel

from api.models.utils import utc_now


class ChatMessage(SQLModel, table=True):
    """A message in a song's conversation history."""

    __tablename__ = "chat_messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    song_id: uuid.UUID = Field(foreign_key="songs.id", index=True)

    # Message role: 'user' or 'assistant'
    role: str = Field(max_length=20)

    # Message content
    content: str

    # Optional metadata for assistant messages
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_cost_usd: Optional[Decimal] = None
    duration_ms: Optional[int] = None
    model: Optional[str] = Field(default=None, max_length=100)

    # Timestamp
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=True), nullable=False, server_default=text("now()")),
    )
