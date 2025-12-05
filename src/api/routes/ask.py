"""
Document Q&A routes.

Endpoints:
    POST /ask  - Ask a question about documents (streaming response)
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import StreamingResponse

from src.api.schemas import QuestionRequest, AnswerResponse
from src.api.dependencies import get_unified_qa_chain
from src.api.rate_limit import limiter
from src.auth import CurrentUser
from src.rag.chain import UnifiedQAChain
from src.config.errors import ErrorMessages
from src.security.sanitization import sanitize_query_string, validate_model_name, validate_parameter_bounds

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/ask", response_model=AnswerResponse)
@limiter.limit("60/minute")
async def ask_question(
    request: Request,
    user: CurrentUser,
    question_request: QuestionRequest,
    qa_chain: UnifiedQAChain = Depends(get_unified_qa_chain),
):
    """Ask a question about a processed document."""

    # Sanitize query string
    question = sanitize_query_string(question_request.question)
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Validate model name if provided
    if question_request.model_name and not validate_model_name(question_request.model_name):
        raise HTTPException(status_code=400, detail="Invalid model name")

    # Validate and sanitize other parameters
    params = validate_parameter_bounds(
        {
            "temperature": question_request.temperature,
            "max_results": question_request.max_results,
        }
    )
    temperature = params.get("temperature", question_request.temperature)
    max_results = params.get("max_results", question_request.max_results)

    try:
        logger.info(f"Question: {question} for document: {question_request.document_id}")

        return await _ask_question_impl(
            question=question,
            question_request=question_request,
            temperature=temperature,
            max_results=max_results,
            qa_chain=qa_chain,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing question: {e}", exc_info=True)
        context = {"model_name": question_request.model_name}
        error_msg = ErrorMessages.get_specific_error(e, context)
        raise HTTPException(status_code=500, detail=error_msg)


async def _ask_question_impl(
    question: str,
    question_request: QuestionRequest,
    temperature: float,
    max_results: int,
    qa_chain: UnifiedQAChain,
):
    """Implementation of ask question with streaming support."""
    try:
        # Create streaming generator
        result = qa_chain.answer_question(
            question=question,
            document_id=question_request.document_id,
            use_web=question_request.use_web_search,
            max_results=max_results,
            model_name=question_request.model_name,
            temperature=temperature,
            streaming=True,
        )

        # Return streaming response
        return StreamingResponse(
            result["stream"],
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",  # Disable proxy buffering
            },
        )

    except ValueError as e:
        error_msg = ErrorMessages.DOCUMENT_NOT_FOUND
        raise HTTPException(status_code=404, detail=error_msg)
