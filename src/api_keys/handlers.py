"""
Exception handlers for API key errors.

Converts domain exceptions to HTTP responses.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from src.api_keys.exceptions import APIKeyError, APIKeyNotFoundError


_STATUS_CODES: dict[type[APIKeyError], int] = {
    APIKeyNotFoundError: status.HTTP_404_NOT_FOUND,
}


async def api_key_exception_handler(request: Request, exc: APIKeyError) -> JSONResponse:
    """Handle API key exceptions."""
    status_code = _STATUS_CODES.get(type(exc), status.HTTP_400_BAD_REQUEST)

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message},
    )


def register_api_key_exception_handlers(app: FastAPI) -> None:
    """Register API key exception handlers with the app."""
    app.add_exception_handler(APIKeyError, api_key_exception_handler)
