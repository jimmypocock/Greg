"""Agent review database store."""

import logging
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.songwriter.enums import AgentTaskType, AgentType
from apps.songwriter.models import AgentReview

logger = logging.getLogger(__name__)


class AgentReviewStore:
    """Database store for agent reviews."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        song_id: UUID,
        agent_type: AgentType,
        task_type: AgentTaskType,
        result: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        total_cost_usd: Decimal = Decimal("0"),
        duration_ms: Optional[int] = None,
        model: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> AgentReview:
        """Create a new agent review."""
        review = AgentReview(
            song_id=song_id,
            agent_type=agent_type,
            task_type=task_type,
            result=result,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_cost_usd=total_cost_usd,
            duration_ms=duration_ms,
            model=model,
            success=success,
            error_message=error_message,
        )

        self.session.add(review)
        await self.session.commit()
        await self.session.refresh(review)

        logger.info(
            f"Stored agent review: song={song_id}, agent={agent_type.value}, "
            f"task={task_type.value}, tokens={input_tokens}+{output_tokens}, "
            f"cost=${total_cost_usd:.6f}"
        )

        return review

    async def get(self, review_id: UUID) -> Optional[AgentReview]:
        """Get a review by ID."""
        result = await self.session.execute(
            select(AgentReview).where(AgentReview.id == review_id)
        )
        return result.scalar_one_or_none()

    async def get_by_song(
        self,
        song_id: UUID,
        agent_type: Optional[AgentType] = None,
        limit: int = 50,
    ) -> list[AgentReview]:
        """Get reviews for a song, optionally filtered by agent type."""
        stmt = (
            select(AgentReview)
            .where(AgentReview.song_id == song_id)
            .order_by(AgentReview.created_at.desc())
            .limit(limit)
        )

        if agent_type:
            stmt = stmt.where(AgentReview.agent_type == agent_type)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_total_cost_for_song(self, song_id: UUID) -> Decimal:
        """Get total AI cost spent on a song."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(func.sum(AgentReview.total_cost_usd))
            .where(AgentReview.song_id == song_id)
        )
        total = result.scalar_one_or_none()
        return total or Decimal("0")

    async def delete(self, review_id: UUID) -> bool:
        """Delete a review."""
        review = await self.get(review_id)
        if review:
            await self.session.delete(review)
            await self.session.commit()
            return True
        return False
