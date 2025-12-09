"""
Web search routes.

Provides web search with AI-generated answers.

Endpoints:
    POST /web-search  - Search the web and get an AI-generated answer
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from src.api.dependencies import get_config
from src.api.rate_limit import limiter
from src.auth import CurrentUser
from src.config.settings import Config
from src.search import WebSearchRequest, WebSearchService

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependencies


async def get_search_service(
    config: Annotated[Config, Depends(get_config)],
) -> WebSearchService:
    """Get web search service with config."""
    return WebSearchService(config=config)


# Routes


@router.post("/web-search")
@limiter.limit("30/minute")
async def web_search(
    request: Request,
    user: CurrentUser,
    search_request: WebSearchRequest,
    service: Annotated[WebSearchService, Depends(get_search_service)],
):
    """Search the web for information and get an AI-generated answer."""
    logger.info(f"Web search: {search_request.question}")

    stream = service.search_stream(
        question=search_request.question,
        model_name=search_request.model_name,
        temperature=search_request.temperature,
        max_results=search_request.max_results,
    )

    return StreamingResponse(
        stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
