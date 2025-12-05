"""
Background worker for document processing.

Handles document upload and processing with progress updates.
"""

import asyncio
import logging
import time
from pathlib import Path
from typing import Any

from src.jobs import job_manager, JobType
from src.websocket import (
    connection_manager,
    create_job_progress_event,
    create_job_completed_event,
    create_job_failed_event,
)

logger = logging.getLogger(__name__)


async def process_document_async(
    job_id: str,
    file_path: Path,
    filename: str,
    chunk_size: int,
    doc_processor: Any,
) -> dict[str, Any]:
    """
    Process a document with progress updates.

    Args:
        job_id: The job ID for progress tracking.
        file_path: Path to the uploaded file.
        filename: Original filename.
        chunk_size: Chunk size for splitting.
        doc_processor: DocumentProcessor instance.

    Returns:
        Processing result with document info.
    """
    try:
        start_time = time.time()

        # Stage 1: File received
        await _update_progress(job_id, "received", 10, "File received, starting processing")

        # Stage 2: Reading file
        await _update_progress(job_id, "reading", 20, f"Reading {filename}")

        # Stage 3: Parsing document
        await _update_progress(job_id, "parsing", 30, "Parsing document content")

        # Run the synchronous document processing in a thread pool
        loop = asyncio.get_event_loop()

        # Stage 4: Chunking - We need to break up the process_file call
        # For now, we'll simulate progress during the blocking call
        await _update_progress(job_id, "chunking", 50, "Splitting into chunks")

        # This is the heavy part - runs in thread pool to not block
        result = await loop.run_in_executor(
            None,
            lambda: doc_processor.process_file(
                str(file_path), filename, chunk_size=chunk_size
            ),
        )

        doc_id, pages, chunks, processing_time = result

        # Stage 5: Embedding
        await _update_progress(
            job_id,
            "embedding",
            80,
            f"Generated {chunks} embeddings",
            {"chunks": chunks},
        )

        # Stage 6: Indexing
        await _update_progress(job_id, "indexing", 90, "Adding to vector store")

        # Complete
        processing_time = time.time() - start_time

        result_data = {
            "document_id": doc_id,
            "filename": filename,
            "pages": pages,
            "chunks": chunks,
            "processing_time": round(processing_time, 2),
        }

        await job_manager.complete_job(job_id, result_data)

        # Broadcast completion
        await connection_manager.broadcast_to_job(
            job_id, create_job_completed_event(job_id, result_data)
        )

        logger.info(f"Job {job_id}: Document processing complete - {filename}")
        return result_data

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Job {job_id}: Document processing failed - {error_msg}")

        await job_manager.fail_job(job_id, error_msg)

        # Broadcast failure
        await connection_manager.broadcast_to_job(
            job_id, create_job_failed_event(job_id, error_msg)
        )

        raise


async def process_url_async(
    job_id: str,
    url: str,
    chunk_size: int,
    config: Any,
    doc_processor: Any,
) -> dict[str, Any]:
    """
    Process a URL with progress updates.

    Args:
        job_id: The job ID for progress tracking.
        url: The URL to process.
        chunk_size: Chunk size for splitting.
        config: Application config.
        doc_processor: DocumentProcessor instance.

    Returns:
        Processing result with document info.
    """
    import uuid
    from urllib.parse import urlparse

    from src.rag.web_search import WebSearcher
    from src.security.sanitization import create_safe_file_path
    from src.utils.async_io import write_file_async, delete_file_async

    try:
        start_time = time.time()

        # Stage 1: URL received
        await _update_progress(job_id, "received", 10, "URL received, starting fetch")

        # Stage 2: Fetching content
        await _update_progress(job_id, "fetching", 30, f"Fetching content from {url}")

        loop = asyncio.get_event_loop()

        # Fetch content in thread pool
        searcher = WebSearcher()
        content = await loop.run_in_executor(
            None, lambda: searcher.extract_content(url)
        )

        if not content:
            raise ValueError("Could not extract content from URL")

        # Stage 3: Parsing content
        await _update_progress(job_id, "parsing", 50, "Parsing web content")

        parsed_url = urlparse(url)
        title = f"Web: {parsed_url.netloc}"

        # Create temporary file
        safe_filename = f"web_{uuid.uuid4().hex[:8]}.txt"
        safe_path = create_safe_file_path(safe_filename, config.UPLOAD_DIR)

        if not safe_path:
            raise ValueError("Could not create temporary file")

        try:
            web_content = f"# {title}\n\nSource: {url}\n\n{content}"
            await write_file_async(safe_path, web_content)

            # Stage 4: Processing
            await _update_progress(job_id, "processing", 70, "Processing document")

            result = await loop.run_in_executor(
                None,
                lambda: doc_processor.process_file(
                    str(safe_path), safe_filename, chunk_size=chunk_size
                ),
            )

            doc_id, pages, chunks, _ = result

            # Clean up
            await delete_file_async(safe_path)

            # Stage 5: Complete
            processing_time = time.time() - start_time

            result_data = {
                "document_id": doc_id,
                "filename": safe_filename,
                "source_url": url,
                "pages": 1,
                "chunks": chunks,
                "processing_time": round(processing_time, 2),
            }

            await job_manager.complete_job(job_id, result_data)

            # Broadcast completion
            await connection_manager.broadcast_to_job(
                job_id, create_job_completed_event(job_id, result_data)
            )

            logger.info(f"Job {job_id}: URL processing complete - {url}")
            return result_data

        except Exception as e:
            if safe_path and safe_path.exists():
                safe_path.unlink()
            raise

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Job {job_id}: URL processing failed - {error_msg}")

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
