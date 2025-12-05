"""
Storage statistics routes.

Endpoints:
    GET  /storage  - Get vector store statistics
"""

import logging
from fastapi import APIRouter, HTTPException, Depends

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.auth import CurrentUser
from src.database.models import Document, DocumentChunk, EmbeddingProvider

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/storage")
async def get_storage_stats(
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Get storage statistics for document chunks."""
    try:
        # Count documents
        doc_count = await session.execute(
            select(func.count(Document.id))
        )
        total_documents = doc_count.scalar() or 0

        # Count chunks
        chunk_count = await session.execute(
            select(func.count(DocumentChunk.id))
        )
        total_chunks = chunk_count.scalar() or 0

        # Count by embedding provider
        provider_stats = {}
        for provider in EmbeddingProvider:
            count_result = await session.execute(
                select(func.count(DocumentChunk.id))
                .where(DocumentChunk.embedding_provider == provider)
            )
            count = count_result.scalar() or 0
            if count > 0:
                provider_stats[provider.value] = count

        return {
            "total_documents": total_documents,
            "total_chunks": total_chunks,
            "chunks_by_provider": provider_stats,
            "storage_type": "pgvector",
        }

    except Exception as e:
        logger.error(f"Error getting storage stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to get storage stats")
