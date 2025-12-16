"""
RAG Query Service using pgvector.

Clean implementation for document Q&A with streaming support.
"""

import json
import uuid
from typing import AsyncGenerator, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.database.models import Document, DocumentChunk, EmbeddingProvider
from packages.core.llm import get_provider
from packages.core.llm.embeddings import get_embeddings
from packages.core.config.settings import Config


class QueryService:
    """
    RAG query service using pgvector for retrieval and LLM for generation.
    """

    def __init__(
        self,
        session: AsyncSession,
        config: Optional[Config] = None,
    ):
        self.session = session
        self.config = config or Config()

    async def query(
        self,
        question: str,
        document_id: Optional[uuid.UUID] = None,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        temperature: float = 0.7,
        max_chunks: int = 5,
        stream: bool = True,
    ) -> AsyncGenerator[str, None] | dict:
        """
        Query documents and generate an answer.

        Args:
            question: The user's question
            document_id: Optional - limit search to specific document
            model_name: LLM model to use (defaults to config)
            provider: LLM provider to use (defaults to config)
            temperature: Response temperature
            max_chunks: Max chunks to retrieve for context
            stream: Whether to stream the response

        Returns:
            If stream=True: AsyncGenerator yielding SSE events
            If stream=False: Dict with answer and metadata
        """
        # Get relevant chunks from pgvector
        chunks = await self._retrieve_chunks(question, document_id, max_chunks)

        if not chunks:
            if stream:
                return self._stream_no_context_response(question)
            return {
                "answer": "No relevant documents found. Please upload a document first.",
                "sources": [],
                "chunks_used": 0,
            }

        # Build context from chunks
        context = self._build_context(chunks)
        sources = self._extract_sources(chunks)

        # Generate response
        if stream:
            return self._stream_response(
                question=question,
                context=context,
                sources=sources,
                model_name=model_name,
                provider=provider,
                temperature=temperature,
            )
        else:
            return await self._generate_response(
                question=question,
                context=context,
                sources=sources,
                model_name=model_name,
                provider=provider,
                temperature=temperature,
            )

    async def _retrieve_chunks(
        self,
        question: str,
        document_id: Optional[uuid.UUID],
        max_chunks: int,
    ) -> list[tuple[DocumentChunk, float]]:
        """Retrieve relevant chunks using pgvector similarity search."""
        # Get embeddings for the query
        embeddings = get_embeddings(
            provider=self.config.EMBEDDING_PROVIDER,
            model=self.config.EMBEDDING_MODEL,
        )
        query_embedding = embeddings.embed_query(question)

        # Determine which embedding column to search
        # Check what provider the existing chunks use
        provider_check = await self.session.execute(
            select(DocumentChunk.embedding_provider).limit(1)
        )
        row = provider_check.scalar_one_or_none()

        if row is None:
            return []  # No chunks in database

        chunk_provider = row if isinstance(row, EmbeddingProvider) else EmbeddingProvider(row)

        # Get the appropriate embedding column
        embedding_column = DocumentChunk.get_embedding_column(chunk_provider)

        # Build similarity search query
        stmt = (
            select(
                DocumentChunk,
                embedding_column.cosine_distance(query_embedding).label('distance')
            )
            .where(DocumentChunk.embedding_provider == chunk_provider)
        )

        if document_id:
            stmt = stmt.where(DocumentChunk.document_id == document_id)

        stmt = stmt.order_by('distance').limit(max_chunks)

        result = await self.session.execute(stmt)
        rows = result.all()

        # Convert distance to similarity score (1 - distance)
        return [(row.DocumentChunk, 1 - row.distance) for row in rows]

    def _build_context(self, chunks: list[tuple[DocumentChunk, float]]) -> str:
        """Build context string from retrieved chunks."""
        context_parts = []
        for chunk, score in chunks:
            filename = chunk.chunk_metadata.get('filename', 'Unknown')
            context_parts.append(f"[From: {filename}]\n{chunk.content}")
        return "\n\n---\n\n".join(context_parts)

    def _extract_sources(self, chunks: list[tuple[DocumentChunk, float]]) -> list[dict]:
        """Extract unique sources from chunks."""
        seen = set()
        sources = []
        for chunk, score in chunks:
            doc_id = str(chunk.document_id)
            if doc_id not in seen:
                seen.add(doc_id)
                sources.append({
                    "document_id": doc_id,
                    "filename": chunk.chunk_metadata.get('filename', 'Unknown'),
                    "relevance_score": round(score, 3),
                })
        return sources

    async def _stream_no_context_response(self, question: str) -> AsyncGenerator[str, None]:
        """Stream a response when no context is available."""
        message = "No relevant documents found. Please upload a document first."
        yield f"data: {json.dumps({'token': message})}\n\n"
        yield f"data: {json.dumps({'done': True, 'sources': [], 'chunks_used': 0})}\n\n"

    async def _stream_response(
        self,
        question: str,
        context: str,
        sources: list[dict],
        model_name: Optional[str],
        provider: Optional[str],
        temperature: float,
    ) -> AsyncGenerator[str, None]:
        """Stream the LLM response as SSE events."""
        # Get LLM provider
        llm = get_provider(
            provider=provider or self.config.LLM_PROVIDER,
            model=model_name,
            temperature=temperature,
        )

        # Build prompt
        prompt = self._build_prompt(question, context)

        # Stream response
        full_response = ""
        try:
            for token in llm.generate_stream(prompt):
                full_response += token
                yield f"data: {json.dumps({'token': token})}\n\n"

            # Send completion event
            yield f"data: {json.dumps({'done': True, 'sources': sources, 'chunks_used': len(sources)})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    async def _generate_response(
        self,
        question: str,
        context: str,
        sources: list[dict],
        model_name: Optional[str],
        provider: Optional[str],
        temperature: float,
    ) -> dict:
        """Generate a non-streaming response."""
        # Get LLM provider
        llm = get_provider(
            provider=provider or self.config.LLM_PROVIDER,
            model=model_name,
            temperature=temperature,
        )

        # Build prompt
        prompt = self._build_prompt(question, context)

        # Generate response
        response = llm.generate(prompt)

        return {
            "answer": response.content,
            "sources": sources,
            "chunks_used": len(sources),
            "model": response.model,
            "tokens_used": response.total_tokens,
        }

    def _build_prompt(self, question: str, context: str) -> str:
        """Build the RAG prompt."""
        return f"""Use the following context to answer the question. If the context doesn't contain relevant information, say so.

Context:
{context}

Question: {question}

Answer:"""


async def get_query_service(session: AsyncSession) -> QueryService:
    """Factory function for query service."""
    return QueryService(session=session)
