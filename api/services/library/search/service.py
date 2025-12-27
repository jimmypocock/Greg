"""
Web search service.

Handles web search with LLM-generated responses.
"""

import json
import logging
from typing import AsyncGenerator, Optional

from api.config.settings import Config
from api.llm import get_provider
from api.services.library.rag.web_search import WebSearcher

logger = logging.getLogger(__name__)


class WebSearchService:
    """
    Web search service with LLM response generation.

    Searches the web and generates AI responses from search results.
    """

    # Singleton web searcher instance
    _searcher: WebSearcher | None = None

    def __init__(self, config: Optional[Config] = None):
        self.config = config or Config()

    @classmethod
    def _get_searcher(cls) -> WebSearcher:
        """Get or create the web searcher singleton."""
        if cls._searcher is None:
            cls._searcher = WebSearcher()
        return cls._searcher

    async def search_stream(
        self,
        question: str,
        model_name: Optional[str] = None,
        temperature: float = 0.7,
        max_results: int = 3,
    ) -> AsyncGenerator[str, None]:
        """
        Search the web and stream an LLM response.

        Args:
            question: The search query
            model_name: LLM model to use
            temperature: Response temperature
            max_results: Number of search results to use

        Yields:
            SSE-formatted events with tokens and completion data
        """
        searcher = self._get_searcher()
        results = searcher.search_and_extract(question, num_results=max_results)

        if not results:
            yield f"data: {json.dumps({'token': 'No web search results found.'})}\n\n"
            yield f"data: {json.dumps({'done': True, 'sources': []})}\n\n"
            return

        context, sources = self._build_context(results)
        prompt = self._build_prompt(question, context)

        llm = get_provider(
            provider=self.config.LLM_PROVIDER,
            model=model_name,
            temperature=temperature,
        )

        try:
            for token in llm.generate_stream(prompt):
                yield f"data: {json.dumps({'token': token})}\n\n"

            yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"

        except Exception as e:
            logger.error(f"Error streaming web search response: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    def _build_context(self, results: list) -> tuple[str, list[dict]]:
        """Build context and sources from search results."""
        context_parts = []
        sources = []

        for result in results:
            if result.content:
                context_parts.append(
                    f"[Source: {result.title}]\nURL: {result.url}\n{result.content}"
                )
                sources.append({
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.snippet,
                })

        return "\n\n---\n\n".join(context_parts), sources

    def _build_prompt(self, question: str, context: str) -> str:
        """Build the LLM prompt."""
        return f"""Use the following web search results to answer the question. Include relevant information from the sources.

Web Search Results:
{context}

Question: {question}

Answer:"""


async def get_web_search_service() -> WebSearchService:
    """Factory function for web search service."""
    return WebSearchService()
