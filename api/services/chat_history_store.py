"""
Chat history persistence service.

Stores and retrieves conversation messages for songs.
"""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.chat_message import ChatMessage


logger = logging.getLogger(__name__)


class ChatHistoryStore:
    """Service for storing and retrieving chat messages."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_message(
        self,
        song_id: UUID,
        role: str,
        content: str,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        total_cost_usd: Decimal | None = None,
        duration_ms: int | None = None,
        model: str | None = None,
    ) -> ChatMessage:
        """Add a message to the conversation history."""
        message = ChatMessage(
            song_id=song_id,
            role=role,
            content=content,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost_usd=total_cost_usd,
            duration_ms=duration_ms,
            model=model,
        )
        self.session.add(message)
        await self.session.commit()
        await self.session.refresh(message)
        return message

    async def get_history(
        self,
        song_id: UUID,
        limit: int = 50,
    ) -> list[ChatMessage]:
        """Get conversation history for a song, ordered by creation time."""
        query = (
            select(ChatMessage)
            .where(ChatMessage.song_id == song_id)
            .order_by(ChatMessage.created_at.asc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_history_for_context(
        self,
        song_id: UUID,
        limit: int = 20,
    ) -> list[dict]:
        """Get conversation history formatted for agent context.

        Returns a list of {role, content} dicts suitable for passing
        to the agent as conversation history.
        """
        messages = await self.get_history(song_id, limit=limit)
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    async def clear_history(self, song_id: UUID) -> int:
        """Clear all messages for a song. Returns count of deleted messages."""
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(ChatMessage).where(ChatMessage.song_id == song_id)
        )
        await self.session.commit()
        return result.rowcount
