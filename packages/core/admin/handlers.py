"""
Exception handlers for admin errors.

Converts domain exceptions to HTTP responses.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from packages.core.admin.exceptions import (
    AdminError,
    CannotDeleteSelfError,
    CannotDemoteSelfError,
    CannotDisableSelfError,
    InvalidRoleError,
    InviteAlreadyUsedError,
    InviteGenerationError,
    InviteNotFoundError,
    UserNotFoundError,
)


_STATUS_CODES: dict[type[AdminError], int] = {
    UserNotFoundError: status.HTTP_404_NOT_FOUND,
    InviteNotFoundError: status.HTTP_404_NOT_FOUND,
    CannotDeleteSelfError: status.HTTP_400_BAD_REQUEST,
    CannotDemoteSelfError: status.HTTP_400_BAD_REQUEST,
    CannotDisableSelfError: status.HTTP_400_BAD_REQUEST,
    InviteAlreadyUsedError: status.HTTP_400_BAD_REQUEST,
    InvalidRoleError: status.HTTP_400_BAD_REQUEST,
    InviteGenerationError: status.HTTP_500_INTERNAL_SERVER_ERROR,
}


async def admin_exception_handler(request: Request, exc: AdminError) -> JSONResponse:
    """Handle admin exceptions."""
    status_code = _STATUS_CODES.get(type(exc), status.HTTP_400_BAD_REQUEST)

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message},
    )


def register_admin_exception_handlers(app: FastAPI) -> None:
    """Register admin exception handlers with the app."""
    app.add_exception_handler(AdminError, admin_exception_handler)
