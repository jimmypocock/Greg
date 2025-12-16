"""
Storage service.

Provides business logic for vector store statistics.
"""

import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database.models import Document, DocumentChunk, EmbeddingProvider
from apps.writer.services.storage.exceptions import StorageStatsError
from apps.writer.services.storage.schemas import StorageStatsResponse

logger = logging.getLogger(__name__)


class StorageService:
    """Service for storage operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_stats(self, user_id: UUID | None = None) -> StorageStatsResponse:
        """
        Get storage statistics.

        Args:
            user_id: Optional user ID to filter stats (not currently used).

        Returns:
            Storage statistics response.

        Raises:
            StorageStatsError: If stats cannot be retrieved.
        """
        try:
            total_documents = await self._count_documents()
            total_chunks = await self._count_chunks()
            chunks_by_provider = await self._count_chunks_by_provider()

            return StorageStatsResponse(
                chunks_by_provider=chunks_by_provider,
                storage_type="pgvector",
                total_chunks=total_chunks,
                total_documents=total_documents,
            )

        except Exception as e:
            logger.error(f"Error getting storage stats: {e}")
            raise StorageStatsError()

    async def _count_documents(self) -> int:
        """Count total documents."""
        result = await self.session.execute(select(func.count(Document.id)))
        return result.scalar() or 0

    async def _count_chunks(self) -> int:
        """Count total document chunks."""
        result = await self.session.execute(select(func.count(DocumentChunk.id)))
        return result.scalar() or 0

    async def _count_chunks_by_provider(self) -> dict[str, int]:
        """Count chunks grouped by embedding provider."""
        provider_stats = {}

        for provider in EmbeddingProvider:
            result = await self.session.execute(
                select(func.count(DocumentChunk.id)).where(
                    DocumentChunk.embedding_provider == provider
                )
            )
            count = result.scalar() or 0
            if count > 0:
                provider_stats[provider.value] = count

        return provider_stats
