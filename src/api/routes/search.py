"""
Web search routes.

Endpoints:
    POST /web-search  - Search the web (streaming response)
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse

from src.api.schemas import QuestionRequest
from src.api.dependencies import get_unified_qa_chain
from src.api.rate_limit import limiter
from src.auth import CurrentUser
from src.rag.chain import UnifiedQAChain
from src.config.errors import ErrorMessages
from src.security.sanitization import sanitize_query_string, validate_model_name

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/web-search")
@limiter.limit("30/minute")
async def web_search(
    request: Request,
    user: CurrentUser,
    question_request: QuestionRequest,
    qa_chain: UnifiedQAChain = Depends(get_unified_qa_chain),
):
    """Search the web for information without requiring a document."""
    # Sanitize query string
    question = sanitize_query_string(question_request.question)
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Validate model name if provided
    if question_request.model_name and not validate_model_name(question_request.model_name):
        raise HTTPException(status_code=400, detail="Invalid model name")

    try:
        logger.info(f"Web search: {question}")

        result = qa_chain.answer_question(
            question=question,
            document_id="web_only",
            use_web=True,
            max_results=question_request.max_results or 5,
            model_name=question_request.model_name,
            temperature=question_request.temperature,
            streaming=True,
        )

        return StreamingResponse(
            result["stream"],
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            },
        )

    except Exception as e:
        logger.error(f"Error in web search: {e}")
        error_msg = ErrorMessages.get_specific_error(e, {"context": "web_search"})
        raise HTTPException(status_code=500, detail=error_msg)
