"""
Document Q&A routes.

Provides question-answering over uploaded documents.

Endpoints:
    POST /ask - Ask a question about documents (streaming or JSON response)
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.api.dependencies import get_config
from packages.core.api.rate_limit import limiter
from apps.writer.services.ask import QuestionRequest
from packages.core.auth import CurrentUser
from packages.core.config.settings import Config
from packages.core.database import get_session_dependency
from apps.writer.services.rag.query_service import QueryService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Q&A"])


# Dependencies


async def get_query_service(
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
    config: Annotated[Config, Depends(get_config)],
) -> QueryService:
    """Get query service with session and config."""
    return QueryService(session=session, config=config)


# Routes


@router.post("/ask")
@limiter.limit("60/minute")
async def ask_question(
    request: Request,
    user: CurrentUser,
    question_request: QuestionRequest,
    service: Annotated[QueryService, Depends(get_query_service)],
):
    """
    Ask a question about uploaded documents.

    Returns streaming SSE response if stream=True, otherwise JSON response.
    """
    result = await service.query(
        question=question_request.question,
        document_id=question_request.get_document_uuid(),
        model_name=question_request.model_name,
        temperature=question_request.temperature,
        max_chunks=question_request.max_results,
        stream=question_request.stream,
    )

    if question_request.stream:
        return StreamingResponse(
            result,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        return JSONResponse(content=result)
