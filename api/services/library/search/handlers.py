"""
Exception handlers for search errors.

Converts domain exceptions to HTTP responses.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from api.services.library.search.exceptions import (
    EmptyQueryError,
    InvalidModelError,
    SearchError,
    WebSearchError,
)


_STATUS_CODES: dict[type[SearchError], int] = {
    EmptyQueryError: status.HTTP_400_BAD_REQUEST,
    InvalidModelError: status.HTTP_400_BAD_REQUEST,
    WebSearchError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


async def search_exception_handler(request: Request, exc: SearchError) -> JSONResponse:
    """Handle search exceptions."""
    status_code = _STATUS_CODES.get(type(exc), status.HTTP_400_BAD_REQUEST)

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message},
    )


def register_search_exception_handlers(app: FastAPI) -> None:
    """Register search exception handlers with the app."""
    app.add_exception_handler(SearchError, search_exception_handler)
