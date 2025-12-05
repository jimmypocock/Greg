"""
pgvector-based vector storage service.

Replaces FAISS with PostgreSQL + pgvector for production-ready vector search.
Supports dual embedding columns for different providers.
"""

import uuid
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import DocumentChunk, EmbeddingProvider
from src.llm.embeddings import get_embeddings, get_embedding_dimension


class PgVectorStore:
    """
    Vector store using PostgreSQL + pgvector.

    Supports dual embedding columns:
    - embedding_local (384 dim): sentence-transformers
    - embedding_openai (1536 dim): OpenAI
    """

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: Optional[str] = None,
        embedding_model: Optional[str] = None,
    ):
        """
        Initialize the vector store.

        Args:
            session: SQLAlchemy async session
            embedding_provider: "local" or "openai" (auto-detects if None)
            embedding_model: Specific model to use (provider default if None)
        """
        self.session = session
        self.embeddings = get_embeddings(provider=embedding_provider, model=embedding_model)

        # Determine which provider we're using
        provider_name = embedding_provider or self._detect_provider()
        self.provider = EmbeddingProvider(provider_name)

    def _detect_provider(self) -> str:
        """Detect provider from the embeddings instance."""
        provider_name = getattr(self.embeddings, 'PROVIDER_NAME', 'local')
        return provider_name

    async def add_chunks(
        self,
        document_id: uuid.UUID,
        chunks: list[dict],
    ) -> list[DocumentChunk]:
        """
        Add document chunks with embeddings to the database.

        Args:
            document_id: Parent document UUID
            chunks: List of dicts with 'content', 'metadata', and optionally 'token_count'

        Returns:
            List of created DocumentChunk objects
        """
        # Generate embeddings for all chunks
        texts = [chunk['content'] for chunk in chunks]
        embeddings = self.embeddings.embed_documents(texts)

        # Create chunk objects
        db_chunks = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            db_chunk = DocumentChunk(
                id=uuid.uuid4(),
                document_id=document_id,
                chunk_index=i,
                content=chunk['content'],
                token_count=chunk.get('token_count', 0),
                chunk_metadata=chunk.get('metadata', {}),
                embedding_provider=self.provider,
            )

            # Set the appropriate embedding column
            if self.provider == EmbeddingProvider.LOCAL:
                db_chunk.embedding_local = embedding
            else:
                db_chunk.embedding_openai = embedding

            db_chunks.append(db_chunk)

        # Bulk insert
        self.session.add_all(db_chunks)
        await self.session.flush()

        return db_chunks

    async def similarity_search(
        self,
        query: str,
        document_id: Optional[uuid.UUID] = None,
        k: int = 5,
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Search for similar chunks using cosine similarity.

        Args:
            query: Search query text
            document_id: Optional - limit search to specific document
            k: Number of results to return

        Returns:
            List of (chunk, similarity_score) tuples, ordered by similarity
        """
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)

        # Get the appropriate column for similarity search
        embedding_column = DocumentChunk.get_embedding_column(self.provider)

        # Build query with cosine distance (pgvector uses <=> for cosine)
        # Lower distance = more similar, so we order ASC
        stmt = (
            select(
                DocumentChunk,
                embedding_column.cosine_distance(query_embedding).label('distance')
            )
            .where(DocumentChunk.embedding_provider == self.provider)
        )

        if document_id:
            stmt = stmt.where(DocumentChunk.document_id == document_id)

        stmt = stmt.order_by('distance').limit(k)

        result = await self.session.execute(stmt)
        rows = result.all()

        # Convert distance to similarity (1 - distance for cosine)
        return [(row.DocumentChunk, 1 - row.distance) for row in rows]

    async def similarity_search_with_scores(
        self,
        query: str,
        document_id: Optional[uuid.UUID] = None,
        k: int = 5,
        score_threshold: Optional[float] = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Search with optional score threshold filtering.

        Args:
            query: Search query text
            document_id: Optional - limit search to specific document
            k: Number of results to return
            score_threshold: Minimum similarity score (0-1)

        Returns:
            List of (chunk, similarity_score) tuples
        """
        results = await self.similarity_search(query, document_id, k)

        if score_threshold is not None:
            results = [(chunk, score) for chunk, score in results if score >= score_threshold]

        return results

    async def delete_document_chunks(self, document_id: uuid.UUID) -> int:
        """
        Delete all chunks for a document.

        Args:
            document_id: Document UUID

        Returns:
            Number of chunks deleted
        """
        stmt = delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_document_chunks(
        self,
        document_id: uuid.UUID,
        include_embeddings: bool = False,
    ) -> list[DocumentChunk]:
        """
        Get all chunks for a document.

        Args:
            document_id: Document UUID
            include_embeddings: Whether to load embedding data

        Returns:
            List of DocumentChunk objects
        """
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_chunks(self, document_id: Optional[uuid.UUID] = None) -> int:
        """
        Count chunks, optionally for a specific document.

        Args:
            document_id: Optional document UUID

        Returns:
            Number of chunks
        """
        from sqlalchemy import func

        stmt = select(func.count(DocumentChunk.id))
        if document_id:
            stmt = stmt.where(DocumentChunk.document_id == document_id)

        result = await self.session.execute(stmt)
        return result.scalar() or 0


def get_vector_store(
    session: AsyncSession,
    embedding_provider: Optional[str] = None,
    embedding_model: Optional[str] = None,
) -> PgVectorStore:
    """
    Factory function to get a configured vector store.

    Args:
        session: SQLAlchemy async session
        embedding_provider: "local" or "openai" (auto-detects if None)
        embedding_model: Specific model to use

    Returns:
        Configured PgVectorStore instance
    """
    return PgVectorStore(
        session=session,
        embedding_provider=embedding_provider,
        embedding_model=embedding_model,
    )
