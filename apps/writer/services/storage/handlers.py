"""
Exception handlers for storage errors.

Converts domain exceptions to HTTP responses.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from apps.writer.services.storage.exceptions import StorageError, StorageStatsError


_STATUS_CODES: dict[type[StorageError], int] = {
    StorageStatsError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


async def storage_exception_handler(request: Request, exc: StorageError) -> JSONResponse:
    """Handle storage exceptions."""
    status_code = _STATUS_CODES.get(type(exc), status.HTTP_400_BAD_REQUEST)

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message},
    )


def register_storage_exception_handlers(app: FastAPI) -> None:
    """Register storage exception handlers with the app."""
    app.add_exception_handler(StorageError, storage_exception_handler)
