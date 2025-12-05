"""
Web search routes.

Endpoints:
    POST /web-search  - Search the web and get an AI-generated answer
"""

import json
import logging
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse

from src.api.schemas import QuestionRequest
from src.api.dependencies import get_config
from src.api.rate_limit import limiter
from src.auth import CurrentUser
from src.config.settings import Config
from src.llm import get_provider
from src.rag.web_search import WebSearcher
from src.security.sanitization import sanitize_query_string, validate_model_name

logger = logging.getLogger(__name__)

router = APIRouter()

# Shared web searcher instance
_web_searcher: WebSearcher | None = None


def get_web_searcher() -> WebSearcher:
    """Get or create the web searcher instance."""
    global _web_searcher
    if _web_searcher is None:
        _web_searcher = WebSearcher()
    return _web_searcher


async def _stream_web_search_response(
    question: str,
    config: Config,
    model_name: str | None,
    temperature: float,
    max_results: int,
) -> AsyncGenerator[str, None]:
    """Stream web search results with LLM response."""
    web_searcher = get_web_searcher()

    # Search the web
    results = web_searcher.search_and_extract(question, num_results=max_results)

    if not results:
        yield f"data: {json.dumps({'token': 'No web search results found.'})}\n\n"
        yield f"data: {json.dumps({'done': True, 'sources': []})}\n\n"
        return

    # Build context from search results
    context_parts = []
    sources = []
    for result in results:
        if result.content:
            context_parts.append(f"[Source: {result.title}]\nURL: {result.url}\n{result.content}")
            sources.append({
                "title": result.title,
                "url": result.url,
                "snippet": result.snippet,
            })

    context = "\n\n---\n\n".join(context_parts)

    # Build prompt
    prompt = f"""Use the following web search results to answer the question. Include relevant information from the sources.

Web Search Results:
{context}

Question: {question}

Answer:"""

    # Get LLM provider
    llm = get_provider(
        provider=config.LLM_PROVIDER,
        model=model_name,
        temperature=temperature,
    )

    # Stream response
    try:
        for token in llm.generate_stream(prompt):
            yield f"data: {json.dumps({'token': token})}\n\n"

        yield f"data: {json.dumps({'done': True, 'sources': sources})}\n\n"

    except Exception as e:
        logger.error(f"Error streaming web search response: {e}")
        yield f"data: {json.dumps({'error': str(e)})}\n\n"


@router.post("/web-search")
@limiter.limit("30/minute")
async def web_search(
    request: Request,
    user: CurrentUser,
    question_request: QuestionRequest,
    config: Config = Depends(get_config),
):
    """Search the web for information and get an AI-generated answer."""
    # Sanitize query string
    question = sanitize_query_string(question_request.question)
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Validate model name if provided
    if question_request.model_name and not validate_model_name(question_request.model_name):
        raise HTTPException(status_code=400, detail="Invalid model name")

    logger.info(f"Web search: {question}")

    return StreamingResponse(
        _stream_web_search_response(
            question=question,
            config=config,
            model_name=question_request.model_name,
            temperature=question_request.temperature or 0.7,
            max_results=question_request.max_results or 3,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
