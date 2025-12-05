"""
Document Q&A routes.

Endpoints:
    POST /ask - Ask a question about documents (streaming response)
"""

import logging
import uuid

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import QuestionRequest
from src.api.dependencies import get_config, get_db
from src.api.rate_limit import limiter
from src.auth import CurrentUser
from src.config.settings import Config
from src.rag.query_service import QueryService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/ask")
@limiter.limit("60/minute")
async def ask_question(
    request: Request,
    user: CurrentUser,
    question_request: QuestionRequest,
    db: AsyncSession = Depends(get_db),
    config: Config = Depends(get_config),
):
    """
    Ask a question about uploaded documents.

    Returns a streaming response (SSE) with the answer.

    Request body:
    - question: The question to ask
    - document_id: Optional UUID to limit search to specific document
    - model_name: Optional LLM model override
    - temperature: Optional temperature (0.0-1.0)
    - max_results: Max chunks to retrieve (default 5)

    Response (SSE stream):
    - {"token": "..."} - Partial response tokens
    - {"done": true, "sources": [...], "chunks_used": N} - Completion event
    """
    question = question_request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Parse document_id if provided
    document_id = None
    if question_request.document_id and question_request.document_id not in ("all", "unified"):
        try:
            document_id = uuid.UUID(question_request.document_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document_id format")

    try:
        logger.info(f"Question: {question[:100]}... (doc: {document_id})")

        # Create query service
        service = QueryService(session=db, config=config)

        # Get streaming response
        stream = await service.query(
            question=question,
            document_id=document_id,
            model_name=question_request.model_name,
            temperature=question_request.temperature or 0.7,
            max_chunks=question_request.max_results or 5,
            stream=True,
        )

        return StreamingResponse(
            stream,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
