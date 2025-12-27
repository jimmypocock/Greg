"""
Background worker for document processing.

Handles document upload and processing with progress updates using pgvector storage.
"""

import asyncio
import logging
import uuid
from pathlib import Path
from typing import Any

from sqlalchemy import select

from api.jobs import job_manager
from api.websocket import (
    connection_manager,
    create_job_progress_event,
    create_job_completed_event,
    create_job_failed_event,
)
from api.database import get_session
from api.database.models import Document, DocumentStatus
from api.services.library.documents.service import DocumentService
from api.config.settings import Config

logger = logging.getLogger(__name__)


async def process_document_job(
    job_id: str,
    document_id: uuid.UUID,
    file_path: Path,
    chunk_size: int,
) -> dict[str, Any]:
    """
    Process a document with progress updates.

    Args:
        job_id: The job ID for progress tracking.
        document_id: The document UUID in the database.
        file_path: Path to the uploaded file.
        chunk_size: Chunk size for splitting.

    Returns:
        Processing result with document info.
    """
    async with get_session() as session:
        try:
            # Get document from database
            stmt = select(Document).where(Document.id == document_id)
            result = await session.execute(stmt)
            document = result.scalar_one_or_none()

            if not document:
                raise ValueError(f"Document {document_id} not found")

            # Create document service
            service = DocumentService(session=session)

            # Define progress callback
            async def progress_callback(stage: str, percent: float, message: str):
                await _update_progress(job_id, stage, percent, message)

            # Process the document
            result_data = await service.process_document(
                document=document,
                file_path=file_path,
                chunk_size=chunk_size,
                progress_callback=progress_callback,
            )

            # Commit the transaction
            await session.commit()

            # Mark job as complete
            await job_manager.complete_job(job_id, result_data)

            # Broadcast completion
            await connection_manager.broadcast_to_job(
                job_id, create_job_completed_event(job_id, result_data)
            )

            logger.info(f"Job {job_id}: Document processing complete - {document.name}")

            # Clean up the uploaded file after successful processing
            if file_path.exists():
                file_path.unlink()

            return result_data

        except Exception as e:
            await session.rollback()
            error_msg = str(e)
            logger.error(f"Job {job_id}: Document processing failed - {error_msg}")

            # Update document status to failed
            try:
                stmt = select(Document).where(Document.id == document_id)
                result = await session.execute(stmt)
                document = result.scalar_one_or_none()
                if document:
                    document.status = DocumentStatus.FAILED
                    document.error_message = error_msg
                    await session.commit()
            except Exception:
                pass

            await job_manager.fail_job(job_id, error_msg)

            # Broadcast failure
            await connection_manager.broadcast_to_job(
                job_id, create_job_failed_event(job_id, error_msg)
            )

            raise


async def process_url_job(
    job_id: str,
    document_id: uuid.UUID,
    url: str,
    chunk_size: int,
) -> dict[str, Any]:
    """
    Process a URL with progress updates.

    Args:
        job_id: The job ID for progress tracking.
        document_id: The document UUID in the database.
        url: The URL to process.
        chunk_size: Chunk size for splitting.

    Returns:
        Processing result with document info.
    """
    config = Config()

    async with get_session() as session:
        try:
            # Get document from database
            stmt = select(Document).where(Document.id == document_id)
            result = await session.execute(stmt)
            document = result.scalar_one_or_none()

            if not document:
                raise ValueError(f"Document {document_id} not found")

            # Stage 1: Fetching
            await _update_progress(job_id, "fetching", 20, f"Fetching content from {url}")

            # Fetch URL content
            loop = asyncio.get_event_loop()

            from api.services.library.rag.web_search import WebSearcher

            searcher = WebSearcher()
            content = await loop.run_in_executor(
                None, lambda: searcher.extract_content(url)
            )

            if not content:
                raise ValueError("Could not extract content from URL")

            # Create temporary file
            from api.security.sanitization import create_safe_file_path
            from api.utils.async_io import write_file_async, delete_file_async

            safe_filename = f"web_{uuid.uuid4().hex[:8]}.txt"
            safe_path = create_safe_file_path(safe_filename, config.UPLOAD_DIR)

            if not safe_path:
                raise ValueError("Could not create temporary file")

            try:
                # Write content to temp file
                from urllib.parse import urlparse

                parsed_url = urlparse(url)
                web_content = f"# Web: {parsed_url.netloc}\n\nSource: {url}\n\n{content}"
                await write_file_async(safe_path, web_content)

                # Update document file size
                document.file_size = len(web_content.encode())

                # Create document service
                service = DocumentService(session=session)

                # Define progress callback
                async def progress_callback(stage: str, percent: float, message: str):
                    # Offset progress since we already did fetching
                    adjusted_percent = 20 + (percent * 0.8)
                    await _update_progress(job_id, stage, adjusted_percent, message)

                # Process the document
                result_data = await service.process_document(
                    document=document,
                    file_path=safe_path,
                    chunk_size=chunk_size,
                    progress_callback=progress_callback,
                )

                # Add source URL to result
                result_data["source_url"] = url

                # Commit the transaction
                await session.commit()

                # Mark job as complete
                await job_manager.complete_job(job_id, result_data)

                # Broadcast completion
                await connection_manager.broadcast_to_job(
                    job_id, create_job_completed_event(job_id, result_data)
                )

                logger.info(f"Job {job_id}: URL processing complete - {url}")

                return result_data

            finally:
                # Clean up temp file
                if safe_path and safe_path.exists():
                    await delete_file_async(safe_path)

        except Exception as e:
            await session.rollback()
            error_msg = str(e)
            logger.error(f"Job {job_id}: URL processing failed - {error_msg}")

            # Update document status to failed
            try:
                stmt = select(Document).where(Document.id == document_id)
                result = await session.execute(stmt)
                document = result.scalar_one_or_none()
                if document:
                    document.status = DocumentStatus.FAILED
                    document.error_message = error_msg
                    await session.commit()
            except Exception:
                pass

            await job_manager.fail_job(job_id, error_msg)

            # Broadcast failure
            await connection_manager.broadcast_to_job(
                job_id, create_job_failed_event(job_id, error_msg)
            )

            raise


async def _update_progress(
    job_id: str,
    stage: str,
    percent: float,
    message: str,
    details: dict[str, Any] | None = None,
) -> None:
    """Update job progress and broadcast to subscribers."""
    await job_manager.update_progress(job_id, stage, percent, message, details)

    # Broadcast to WebSocket subscribers
    await connection_manager.broadcast_to_job(
        job_id,
        create_job_progress_event(job_id, stage, percent, message, details),
    )
