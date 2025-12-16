"""
Document processing module.

Provides document service and schemas for document endpoints.
"""

from apps.writer.services.documents.exceptions import (
    DocumentError,
    DocumentNotFoundError,
    FileOperationError,
    InvalidFilenameError,
    InvalidURLError,
    UnsupportedFileTypeError,
)
from apps.writer.services.documents.handlers import register_document_exception_handlers
from apps.writer.services.documents.schemas import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
    JobCreatedResponse,
    MessageResponse,
    URLProcessRequest,
)
from apps.writer.services.documents.service import DocumentService, get_document_service

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
