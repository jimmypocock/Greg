"""
Document processing module.

Provides document service and schemas for document endpoints.
"""

from src.documents.exceptions import (
    DocumentError,
    DocumentNotFoundError,
    FileOperationError,
    InvalidFilenameError,
    InvalidURLError,
    UnsupportedFileTypeError,
)
from src.documents.handlers import register_document_exception_handlers
from src.documents.schemas import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    JobCreatedResponse,
    MessageResponse,
    URLProcessRequest,
)
from src.documents.service import DocumentService, get_document_service

__all__ = [
    # Exceptions
    "DocumentError",
    "DocumentNotFoundError",
    "FileOperationError",
    "InvalidFilenameError",
    "InvalidURLError",
    "UnsupportedFileTypeError",
    # Handlers
    "register_document_exception_handlers",
    # Schemas
    "DocumentDetailResponse",
    "DocumentListResponse",
    "DocumentResponse",
    "JobCreatedResponse",
    "MessageResponse",
    "URLProcessRequest",
    # Service
    "DocumentService",
    "get_document_service",
]
