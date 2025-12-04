"""
Document management routes.

Endpoints:
    POST /upload              - Upload and process a document
    POST /process-url         - Process a URL as a document
    GET /documents            - List all documents
    DELETE /documents/{id}    - Delete a document
    POST /clear-all           - Clear all documents
"""

import os
import json
import shutil
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, Request, UploadFile, File, Form

from src.api.schemas import UploadResponse, URLProcessRequest, MessageResponse
from src.api.dependencies import get_config, get_doc_processor
from src.api.rate_limit import limiter
from src.config.settings import Config
from src.documents.processor import DocumentProcessor
from src.config.errors import ErrorMessages
from src.security.sanitization import sanitize_filename, create_safe_file_path, is_safe_url
from src.utils.async_io import (
    write_file_async,
    delete_file_async,
    load_json_async,
    file_exists_async,
    delete_directory_async,
    read_file_async,
    process_files_batch_async,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    chunk_size: int = Form(800),
    config: Config = Depends(get_config),
    doc_processor: DocumentProcessor = Depends(get_doc_processor),
):
    """
    Upload and process a document at runtime.

    Supports: PDF, TXT, CSV, MD, DOCX, XLSX, PNG, JPG
    The document will be added to the unified vector store.

    Example with curl:
        curl -X POST "http://localhost:8080/upload" \\
            -F "file=@document.pdf" \\
            -F "chunk_size=800"
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

    # Create safe file path
    unique_filename = f"{uuid.uuid4().hex[:8]}_{safe_filename}"
    safe_path = create_safe_file_path(unique_filename, config.UPLOAD_DIR)

    if not safe_path:
        raise HTTPException(status_code=500, detail="Could not create upload path")

    try:
        # Read and write file
        content = await file.read()
        await write_file_async(safe_path, content, mode="wb")

        # Process the document
        doc_id, pages, chunks, processing_time = doc_processor.process_file(
            str(safe_path), safe_filename, chunk_size=chunk_size
        )

        logger.info(f"Uploaded and processed: {safe_filename} -> {doc_id}")

        return UploadResponse(
            document_id=doc_id,
            pages=pages,
            chunks=chunks,
            processing_time=processing_time,
            message=f"Successfully processed {safe_filename}",
        )

    except Exception as e:
        # Clean up on error
        if safe_path and safe_path.exists():
            safe_path.unlink()
        logger.error(f"Error uploading document: {e}")
        error_msg = ErrorMessages.get_specific_error(e, {"context": "upload"})
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/process-url", response_model=UploadResponse)
@limiter.limit("10/minute")
async def process_url(
    request: Request,
    url_request: URLProcessRequest,
    config: Config = Depends(get_config),
    doc_processor: DocumentProcessor = Depends(get_doc_processor),
):
    """Process a URL by fetching and converting its content to a document."""

    # Validate URL
    if not is_safe_url(url_request.url):
        raise HTTPException(
            status_code=400,
            detail="Invalid URL. Please provide a valid HTTP or HTTPS URL.",
        )

    try:
        logger.info(f"Processing URL: {url_request.url}")

        # Fetch and process URL content
        from src.rag.web_search import WebSearcher

        searcher = WebSearcher()

        # Extract content from URL
        content = searcher.extract_content(url_request.url)
        if not content:
            raise HTTPException(status_code=400, detail="Could not extract content from URL")

        # Parse title from content or URL
        from urllib.parse import urlparse

        parsed_url = urlparse(url_request.url)
        title = f"Web: {parsed_url.netloc}"

        # Create a temporary file from the content with secure name
        safe_filename = f"web_{uuid.uuid4().hex[:8]}.txt"
        safe_path = create_safe_file_path(safe_filename, config.UPLOAD_DIR)

        if not safe_path:
            raise HTTPException(status_code=500, detail="Could not create temporary file")

        try:
            # Write web content asynchronously
            web_content = f"# {title}\n\nSource: {url_request.url}\n\n{content}"
            await write_file_async(safe_path, web_content)

            # Process as a text document
            doc_id, pages, chunks, processing_time = doc_processor.process_file(
                str(safe_path),
                safe_filename,
                chunk_size=url_request.chunk_size,
            )

            # Clean up asynchronously
            await delete_file_async(safe_path)

            return UploadResponse(
                document_id=doc_id,
                pages=1,  # Web content is treated as single page
                chunks=chunks,
                processing_time=processing_time,
                message=f"Successfully processed web content from {parsed_url.netloc}",
            )

        except Exception as e:
            if safe_path and safe_path.exists():
                safe_path.unlink()
            raise e

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing URL: {e}")
        error_msg = ErrorMessages.get_specific_error(e, {"context": "url_processing"})
        raise HTTPException(status_code=500, detail=error_msg)


@router.get("/documents")
async def list_documents(config: Config = Depends(get_config)):
    """List all processed documents."""
    try:
        return await _list_documents_impl(config)
    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        from src.security.sanitization import sanitize_error_message

        error_msg = sanitize_error_message(e, show_details=False)
        raise HTTPException(status_code=500, detail=error_msg)


async def _list_documents_impl(config: Config):
    """Implementation of list documents."""
    # Check for unified store first
    unified_metadata_path = config.VECTOR_STORE_DIR / "unified_store.metadata"
    if unified_metadata_path.exists():
        # Load unified store metadata
        unified_metadata = await load_json_async(unified_metadata_path)

        # Convert unified store format to document list format
        documents = []
        for doc in unified_metadata.get("documents", []):
            documents.append(
                {
                    "document_id": "unified",
                    "filename": doc["filename"],
                    "pages": doc["pages"],
                    "chunks": doc["chunks"],
                    "upload_date": unified_metadata["creation_date"],
                    "model_used": unified_metadata["model_used"],
                }
            )

        return {"documents": documents}

    # Fallback to individual document stores
    async def load_metadata(metadata_file):
        # Skip unified store metadata
        if metadata_file.name == "unified_store.metadata":
            return None

        try:
            # Try JSON first (new format)
            metadata = await load_json_async(metadata_file)
            return {
                "document_id": metadata["document_id"],
                "filename": metadata["filename"],
                "pages": metadata["pages"],
                "chunks": metadata.get("chunks", "N/A"),
                "upload_date": metadata["upload_date"],
                "model_used": metadata["model_used"],
            }
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Fallback to pickle for old files
            import pickle

            content = await read_file_async(metadata_file, mode="rb")
            metadata = pickle.loads(content)
            return {
                "document_id": metadata["document_id"],
                "filename": metadata["filename"],
                "pages": metadata["pages"],
                "chunks": metadata.get("chunks", "N/A"),
                "upload_date": metadata["upload_date"].isoformat(),
                "model_used": metadata["model_used"],
            }

    # Process all metadata files concurrently
    metadata_files = list(config.VECTOR_STORE_DIR.glob("*.metadata"))
    results = await process_files_batch_async(metadata_files, load_metadata, max_concurrent=10)
    documents = [doc for doc in results if doc is not None]

    return {"documents": documents}


@router.delete("/documents/{document_id}")
async def delete_document(document_id: str, config: Config = Depends(get_config)):
    """Delete a specific document."""
    try:
        deleted_something = False

        # Delete vector store (it's a directory)
        vector_store_path = config.VECTOR_STORE_DIR / f"{document_id}.faiss"
        if await file_exists_async(vector_store_path) and vector_store_path.is_dir():
            await delete_directory_async(vector_store_path)
            deleted_something = True
            logger.info(f"Deleted vector store for document: {document_id}")

        # Delete metadata
        metadata_path = config.VECTOR_STORE_DIR / f"{document_id}.metadata"
        if await file_exists_async(metadata_path):
            await delete_file_async(metadata_path)
            deleted_something = True
            logger.info(f"Deleted metadata for document: {document_id}")

        if not deleted_something:
            raise HTTPException(status_code=404, detail=f"Document {document_id} not found")

        logger.info(f"Successfully deleted document: {document_id}")
        return {"message": f"Document {document_id} deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {e}", exc_info=True)
        from src.security.sanitization import sanitize_error_message

        error_msg = sanitize_error_message(e, show_details=False)
        raise HTTPException(status_code=500, detail=error_msg)


@router.post("/clear-all")
async def clear_all_documents(config: Config = Depends(get_config)):
    """Clear all documents and reset the system."""
    try:
        # Clear all files in vector store directory
        for file in config.VECTOR_STORE_DIR.glob("*"):
            if file.is_file():
                os.remove(file)
            elif file.is_dir():
                shutil.rmtree(file)

        # Clear uploads directory
        for file in config.UPLOAD_DIR.glob("*"):
            if file.is_file():
                os.remove(file)

        logger.info("Cleared all documents")
        return {"message": "All documents cleared successfully"}

    except Exception as e:
        logger.error(f"Error clearing documents: {e}")
        from src.security.sanitization import sanitize_error_message

        error_msg = sanitize_error_message(e, show_details=False)
        raise HTTPException(status_code=500, detail=error_msg)
