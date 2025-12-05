"""
Document management routes.

Endpoints:
    POST   /documents         - Upload and process a document (async with job)
    POST   /documents/url     - Process a URL as a document (async with job)
    GET    /documents         - List all documents
    GET    /documents/{id}    - Get document details
    DELETE /documents/{id}    - Delete a document
    DELETE /documents         - Clear all documents (admin only)
"""

import asyncio
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas import URLProcessRequest, JobCreatedResponse
from src.api.dependencies import get_config, get_db
from src.api.rate_limit import limiter
from src.auth import Auth, CurrentUser, AdminUser
from src.config.settings import Config
from src.database.models import Document, DocumentStatus, DocumentChunk
from src.security.sanitization import sanitize_filename, create_safe_file_path, is_safe_url
from src.jobs import job_manager, JobType
from src.utils.async_io import write_file_async, delete_file_async

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/documents", response_model=JobCreatedResponse, status_code=202)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    auth: Auth,
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(...),
    chunk_size: int = Form(800),
    config: Config = Depends(get_config),
):
    """
    Upload and process a document asynchronously.

    Returns immediately with a job_id. Connect to the WebSocket endpoint
    to receive real-time progress updates.

    Supports: PDF, TXT, CSV, MD, DOCX, XLSX, PNG, JPG
    """
    # Sanitize filename
    safe_filename = sanitize_filename(file.filename)
    if not safe_filename:
        raise HTTPException(status_code=400, detail="Invalid filename")

    # Validate file extension
    allowed_extensions = {".pdf", ".txt", ".csv", ".md", ".docx", ".xlsx", ".png", ".jpg", ".jpeg"}
    file_ext = Path(safe_filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}",
        )

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Create safe file path for storage
    unique_filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
    safe_path = create_safe_file_path(unique_filename, config.UPLOAD_DIR)

    if not safe_path:
        raise HTTPException(status_code=500, detail="Could not create upload path")

    try:
        # Write file to disk
        await write_file_async(safe_path, content, mode="wb")

        # Create document record in database
        document = Document(
            id=uuid.uuid4(),
            user_id=auth.user.id,
            api_key_id=auth.api_key_id,
            name=safe_filename,
            file_type=file_ext.lstrip("."),
            file_size=file_size,
            storage_key=str(safe_path),
            status=DocumentStatus.PENDING,
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)

        # Create a job for tracking
        job = await job_manager.create_job(JobType.DOCUMENT_UPLOAD)

        # Start background processing
        from src.jobs.document_worker import process_document_job

        asyncio.create_task(
            process_document_job(
                job_id=job.job_id,
                document_id=document.id,
                file_path=safe_path,
                chunk_size=chunk_size,
            )
        )

        logger.info(f"Started upload job {job.job_id} for {safe_filename} (doc_id: {document.id})")

        # Build WebSocket URL from request
        ws_scheme = "wss" if request.url.scheme == "https" else "ws"
        ws_url = f"{ws_scheme}://{request.url.netloc}/ws/jobs/{job.job_id}"

        return JobCreatedResponse(
            job_id=job.job_id,
            status="pending",
            message=f"Processing started for {safe_filename}",
            websocket_url=ws_url,
        )

    except Exception as e:
        # Clean up on error
        if safe_path and safe_path.exists():
            safe_path.unlink()
        logger.error(f"Error starting upload job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/url", response_model=JobCreatedResponse, status_code=202)
@limiter.limit("10/minute")
async def process_url(
    request: Request,
    auth: Auth,
    url_request: URLProcessRequest,
    db: AsyncSession = Depends(get_db),
    config: Config = Depends(get_config),
):
    """
    Process a URL asynchronously by fetching and converting its content.

    Returns immediately with a job_id. Connect to the WebSocket endpoint
    to receive real-time progress updates.
    """
    # Validate URL
    if not is_safe_url(url_request.url):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Please provide a valid HTTP or HTTPS URL.",
        )

    try:
        # Create document record for URL
        from urllib.parse import urlparse

        parsed_url = urlparse(url_request.url)
        url_filename = f"web_{parsed_url.netloc}_{uuid.uuid4().hex[:8]}.txt"

        document = Document(
            id=uuid.uuid4(),
            user_id=auth.user.id,
            api_key_id=auth.api_key_id,
            name=url_filename,
            file_type="url",
            file_size=0,  # Will be updated after fetch
            storage_key=url_request.url,  # Store URL as storage key
            status=DocumentStatus.PENDING,
            extra_metadata={"source_url": url_request.url},
        )
        db.add(document)
        await db.commit()
        await db.refresh(document)

        # Create a job for tracking
        job = await job_manager.create_job(JobType.URL_PROCESS)

        # Start background processing
        from src.jobs.document_worker import process_url_job

        asyncio.create_task(
            process_url_job(
                job_id=job.job_id,
                document_id=document.id,
                url=url_request.url,
                chunk_size=url_request.chunk_size,
            )
        )

        logger.info(f"Started URL processing job {job.job_id} for {url_request.url}")

        # Build WebSocket URL from request
        ws_scheme = "wss" if request.url.scheme == "https" else "ws"
        ws_url = f"{ws_scheme}://{request.url.netloc}/ws/jobs/{job.job_id}"

        return JobCreatedResponse(
            job_id=job.job_id,
            status="pending",
            message=f"Processing started for {url_request.url}",
            websocket_url=ws_url,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting URL processing job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents")
async def list_documents(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """List all documents for the current user."""
    stmt = (
        select(Document)
        .where(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
    )
    result = await db.execute(stmt)
    documents = result.scalars().all()

    return {
        "documents": [
            {
                "id": str(doc.id),
                "name": doc.name,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "status": doc.status.value,
                "chunk_count": doc.chunk_count,
                "error_message": doc.error_message,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "extra_metadata": doc.extra_metadata,
            }
            for doc in documents
        ]
    }


@router.get("/documents/{document_id}")
async def get_document(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get details for a specific document."""
    stmt = select(Document).where(
        Document.id == document_id,
        Document.user_id == user.id,
    )
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "id": str(document.id),
        "name": document.name,
        "file_type": document.file_type,
        "file_size": document.file_size,
        "status": document.status.value,
        "chunk_count": document.chunk_count,
        "total_tokens": document.total_tokens,
        "error_message": document.error_message,
        "created_at": document.created_at.isoformat() if document.created_at else None,
        "updated_at": document.updated_at.isoformat() if document.updated_at else None,
        "extra_metadata": document.extra_metadata,
    }


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: uuid.UUID,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    config: Config = Depends(get_config),
):
    """Delete a specific document and its chunks."""
    # Find document
    stmt = select(Document).where(
        Document.id == document_id,
        Document.user_id == user.id,
    )
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        # Delete file from disk if it exists
        if document.storage_key and not document.storage_key.startswith("http"):
            file_path = Path(document.storage_key)
            if file_path.exists():
                await delete_file_async(file_path)

        # Delete document (chunks cascade automatically)
        await db.delete(document)
        await db.commit()

        logger.info(f"Deleted document {document_id}")
        return {"message": f"Document {document_id} deleted successfully"}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/documents")
async def clear_all_documents(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
    config: Config = Depends(get_config),
):
    """Clear all documents and chunks. Admin only."""
    try:
        # Delete all chunks first (for safety, even though cascade should handle it)
        await db.execute(delete(DocumentChunk))

        # Delete all documents
        await db.execute(delete(Document))

        await db.commit()

        # Clean upload directory
        for file in config.UPLOAD_DIR.glob("*"):
            if file.is_file():
                file.unlink()

        logger.info("Cleared all documents")
        return {"message": "All documents cleared successfully"}

    except Exception as e:
        await db.rollback()
        logger.error(f"Error clearing documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))
