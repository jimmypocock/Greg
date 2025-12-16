"""
Exception handlers for document errors.

Converts domain exceptions to HTTP responses.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from apps.writer.services.documents.exceptions import (
    DocumentError,
    DocumentNotFoundError,
    FileOperationError,
    InvalidFilenameError,
    InvalidURLError,
    UnsupportedFileTypeError,
)


_STATUS_CODES: dict[type[DocumentError], int] = {
    DocumentNotFoundError: status.HTTP_404_NOT_FOUND,
    InvalidFilenameError: status.HTTP_400_BAD_REQUEST,
    InvalidURLError: status.HTTP_400_BAD_REQUEST,
    UnsupportedFileTypeError: status.HTTP_400_BAD_REQUEST,
    FileOperationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


async def document_exception_handler(request: Request, exc: DocumentError) -> JSONResponse:
    """Handle document exceptions."""
    status_code = _STATUS_CODES.get(type(exc), status.HTTP_400_BAD_REQUEST)

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message},
    )


def register_document_exception_handlers(app: FastAPI) -> None:
    """Register document exception handlers with the app."""
    app.add_exception_handler(DocumentError, document_exception_handler)
