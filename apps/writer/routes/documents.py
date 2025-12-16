"""
Document management routes.

Provides document upload, processing, and management endpoints.

Endpoints:
    POST   /documents         - Upload and process a document (async with job)
    POST   /documents/url     - Process a URL as a document (async with job)
    GET    /documents         - List all documents
    GET    /documents/{id}    - Get document details
    DELETE /documents/{id}    - Delete a document
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.api.dependencies import get_config
from packages.core.api.rate_limit import limiter
from packages.core.auth import Auth, CurrentUser
from packages.core.config.settings import Config
from packages.core.database import get_session_dependency
from apps.writer.services.documents import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    DocumentService,
    JobCreatedResponse,
    MessageResponse,
    URLProcessRequest,
)
from packages.core.jobs import JobType, job_manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Documents"])


# Dependencies


async def get_document_service(
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
    config: Annotated[Config, Depends(get_config)],
) -> DocumentService:
    """Get document service with session and config."""
    return DocumentService(session=session, config=config)


# Routes


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


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: uuid.UUID,
    user: CurrentUser,
    service: Annotated[DocumentService, Depends(get_document_service)],
):
    """Get details for a specific document."""
    document = await service.get_document(document_id, user.id)

    return DocumentDetailResponse.from_model(document)


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    user: CurrentUser,
    service: Annotated[DocumentService, Depends(get_document_service)],
):
    """List all documents for the current user."""
    documents = await service.list_documents(user.id)

    return DocumentListResponse(
        documents=[DocumentResponse.from_model(doc) for doc in documents]
    )


@router.post("/documents/url", response_model=JobCreatedResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
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

    from apps.writer.jobs.document_worker import process_url_job

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


@router.post("/documents", response_model=JobCreatedResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    auth: Auth,
    config: Annotated[Config, Depends(get_config)],
    service: Annotated[DocumentService, Depends(get_document_service)],
    file: UploadFile = File(...),
    chunk_size: int = Form(800),
):
    """Upload and process a document asynchronously."""
    content = await file.read()

    document = await service.create_from_file(
        user=auth.user,
        filename=file.filename,
        content=content,
        upload_dir=config.UPLOAD_DIR,
        api_key_id=auth.api_key_id,
    )

    job = await job_manager.create_job(JobType.DOCUMENT_UPLOAD, auth.user.id)

    from apps.writer.jobs.document_worker import process_document_job

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


# Private functions


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
