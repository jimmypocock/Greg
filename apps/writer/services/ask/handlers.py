"""
Exception handlers for ask errors.

Converts domain exceptions to HTTP responses.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from apps.writer.services.ask.exceptions import (
    AskError,
    EmptyQuestionError,
    InvalidDocumentIdError,
    QueryError,
)


_STATUS_CODES: dict[type[AskError], int] = {
    EmptyQuestionError: status.HTTP_400_BAD_REQUEST,
    InvalidDocumentIdError: status.HTTP_400_BAD_REQUEST,
    QueryError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


async def ask_exception_handler(request: Request, exc: AskError) -> JSONResponse:
    """Handle ask exceptions."""
    status_code = _STATUS_CODES.get(type(exc), status.HTTP_400_BAD_REQUEST)

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message},
    )


def register_ask_exception_handlers(app: FastAPI) -> None:
    """Register ask exception handlers with the app."""
    app.add_exception_handler(AskError, ask_exception_handler)
