"""
Exception handlers for job errors.

Converts domain exceptions to HTTP responses.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from packages.core.jobs.exceptions import (
    JobCannotBeCancelledError,
    JobCancellationError,
    JobError,
    JobNotFoundError,
)


_STATUS_CODES: dict[type[JobError], int] = {
    JobNotFoundError: status.HTTP_404_NOT_FOUND,
    JobCannotBeCancelledError: status.HTTP_400_BAD_REQUEST,
    JobCancellationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


async def job_exception_handler(request: Request, exc: JobError) -> JSONResponse:
    """Handle job exceptions."""
    status_code = _STATUS_CODES.get(type(exc), status.HTTP_400_BAD_REQUEST)

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message},
    )


def register_job_exception_handlers(app: FastAPI) -> None:
    """Register job exception handlers with the app."""
    app.add_exception_handler(JobError, job_exception_handler)
