"""
Library routes for document management and RAG queries.

Provides reference library functionality for songwriters:
- Upload and manage reference documents (chord charts, theory, lyrics)
- Query documents using RAG
- Web search for research

Endpoints:
    POST   /library/documents         - Upload a document
    POST   /library/documents/url     - Process a URL as document
    GET    /library/documents         - List all documents
    GET    /library/documents/{id}    - Get document details
    DELETE /library/documents/{id}    - Delete a document
    POST   /library/ask               - Ask a question (RAG query)
    POST   /library/search            - Web search
    GET    /library/stats             - Storage statistics
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from api.api.dependencies import get_config
from api.auth import Auth, CurrentUser
from api.config.settings import Config
from api.database import get_session_dependency
from api.jobs import JobType, job_manager

from api.services.library.documents import (
    DocumentService,
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    JobCreatedResponse,
    MessageResponse,
    URLProcessRequest,
)
from api.services.library.ask import QuestionRequest
from api.services.library.rag.query_service import QueryService
from api.services.library.search.service import WebSearchService
from api.services.library.storage.service import StorageService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/library", tags=["Library"])


# Dependencies


async def get_document_service(
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
    config: Annotated[Config, Depends(get_config)],
) -> DocumentService:
    """Get document service with session and config."""
    return DocumentService(session=session, config=config)


async def get_query_service(
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
    config: Annotated[Config, Depends(get_config)],
) -> QueryService:
    """Get query service with session and config."""
    return QueryService(session=session, config=config)


async def get_storage_service(
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
) -> StorageService:
    """Get storage service."""
    return StorageService(session=session)


# Document Routes


@router.post("/documents", response_model=JobCreatedResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    request: Request,
    auth: Auth,
    config: Annotated[Config, Depends(get_config)],
    service: Annotated[DocumentService, Depends(get_document_service)],
    file: UploadFile = File(...),
    chunk_size: int = Form(800),
):
    """Upload and process a reference document asynchronously."""
    content = await file.read()

    document = await service.create_from_file(
        user=auth.user,
        filename=file.filename,
        content=content,
        upload_dir=config.UPLOAD_DIR,
        api_key_id=auth.api_key_id,
    )

    job = await job_manager.create_job(JobType.DOCUMENT_UPLOAD, auth.user.id)

    from api.jobs.document_worker import process_document_job

    asyncio.create_task(
        process_document_job(
            job_id=job.job_id,
            document_id=document.id,
            file_path=Path(document.storage_key),
            chunk_size=chunk_size,
        )
    )

    logger.info(f"Started upload job {job.job_id} for {document.name} (doc_id: {document.id})")

    return _create_job_response(request, job.job_id, f"Processing started for {document.name}")


@router.post("/documents/url", response_model=JobCreatedResponse, status_code=status.HTTP_202_ACCEPTED)
async def process_url(
    request: Request,
    auth: Auth,
    url_request: URLProcessRequest,
    service: Annotated[DocumentService, Depends(get_document_service)],
):
    """Process a URL asynchronously by fetching and converting its content."""
    document = await service.create_from_url(
        user=auth.user,
        url=url_request.url,
        api_key_id=auth.api_key_id,
    )

    job = await job_manager.create_job(JobType.URL_PROCESS, auth.user.id)

    from api.jobs.document_worker import process_url_job

    asyncio.create_task(
        process_url_job(
            job_id=job.job_id,
            document_id=document.id,
            url=url_request.url,
            chunk_size=url_request.chunk_size,
        )
    )

    logger.info(f"Started URL processing job {job.job_id} for {url_request.url}")

    return _create_job_response(request, job.job_id, f"Processing started for {url_request.url}")


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    user: CurrentUser,
    service: Annotated[DocumentService, Depends(get_document_service)],
):
    """List all documents in the reference library."""
    documents = await service.list_documents(user.id)

    return DocumentListResponse(
        documents=[DocumentResponse.from_model(doc) for doc in documents]
    )


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: uuid.UUID,
    user: CurrentUser,
    service: Annotated[DocumentService, Depends(get_document_service)],
):
    """Get details for a specific document."""
    document = await service.get_document(document_id, user.id)

    return DocumentDetailResponse.from_model(document)


@router.delete("/documents/{document_id}", response_model=MessageResponse)
async def delete_document(
    document_id: uuid.UUID,
    user: CurrentUser,
    service: Annotated[DocumentService, Depends(get_document_service)],
):
    """Delete a specific document and its chunks."""
    await service.delete_document(document_id, user.id)

    logger.info(f"Deleted document {document_id}")

    return MessageResponse(message=f"Document {document_id} deleted successfully")


# RAG Query Routes


@router.post("/ask")
async def ask_question(
    request: Request,
    user: CurrentUser,
    question_request: QuestionRequest,
    service: Annotated[QueryService, Depends(get_query_service)],
):
    """
    Ask a question about your reference library.

    Uses RAG to search relevant documents and generate an answer.
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


# Web Search Route


@router.post("/search")
async def web_search(
    request: Request,
    user: CurrentUser,
    query: str,
    max_results: int = 5,
):
    """
    Search the web for songwriting research.

    Useful for finding rhymes, song meanings, music theory, etc.
    """
    search_service = WebSearchService()

    try:
        results = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: search_service.search(query, max_results=max_results)
        )
        return {"query": query, "results": results}
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


# Storage Stats Route


@router.get("/stats")
async def get_storage_stats(
    user: CurrentUser,
    service: Annotated[StorageService, Depends(get_storage_service)],
):
    """Get storage statistics for the reference library."""
    stats = await service.get_stats(user.id)
    return stats


# Private Functions


def _create_job_response(request: Request, job_id: str, message: str) -> JobCreatedResponse:
    """Create a job response with WebSocket URL."""
    ws_scheme = "wss" if request.url.scheme == "https" else "ws"
    ws_url = f"{ws_scheme}://{request.url.netloc}/ws/jobs/{job_id}"

    return JobCreatedResponse(
        job_id=job_id,
        status="pending",
        message=message,
        websocket_url=ws_url,
    )
