"""
Exception handlers for authentication errors.

Converts domain exceptions to HTTP responses.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from packages.core.auth.exceptions import (
    AuthError,
    EmailAlreadyExistsError,
    ExpiredTokenError,
    InvalidCredentialsError,
    InvalidInviteCodeError,
    InvalidSessionIdError,
    InvalidTokenError,
    RevokedTokenError,
    SessionAlreadyRevokedError,
    SessionNotFoundError,
    UserDisabledError,
    UserNotFoundError,
)


# Exception to HTTP status code mapping
_STATUS_CODES: dict[type[AuthError], int] = {
    # 400 Bad Request
    EmailAlreadyExistsError: status.HTTP_400_BAD_REQUEST,
    InvalidInviteCodeError: status.HTTP_400_BAD_REQUEST,
    InvalidSessionIdError: status.HTTP_400_BAD_REQUEST,
    SessionAlreadyRevokedError: status.HTTP_400_BAD_REQUEST,
    # 401 Unauthorized
    InvalidCredentialsError: status.HTTP_401_UNAUTHORIZED,
    InvalidTokenError: status.HTTP_401_UNAUTHORIZED,
    ExpiredTokenError: status.HTTP_401_UNAUTHORIZED,
    RevokedTokenError: status.HTTP_401_UNAUTHORIZED,
    UserDisabledError: status.HTTP_401_UNAUTHORIZED,
    # 404 Not Found
    SessionNotFoundError: status.HTTP_404_NOT_FOUND,
    UserNotFoundError: status.HTTP_404_NOT_FOUND,
}


def _get_status_code(exc: AuthError) -> int:
    """Get HTTP status code for an exception."""
    return _STATUS_CODES.get(type(exc), status.HTTP_400_BAD_REQUEST)


def _needs_auth_header(exc: AuthError) -> bool:
    """Check if exception should include WWW-Authenticate header."""
    return isinstance(
        exc,
        (InvalidTokenError, ExpiredTokenError, RevokedTokenError),
    )


async def auth_exception_handler(request: Request, exc: AuthError) -> JSONResponse:
    """Handle authentication exceptions."""
    status_code = _get_status_code(exc)
    headers = {"WWW-Authenticate": "Bearer"} if _needs_auth_header(exc) else None

    return JSONResponse(
        status_code=status_code,
        content={"detail": exc.message},
        headers=headers,
    )


def register_auth_exception_handlers(app: FastAPI) -> None:
    """Register all auth exception handlers with the app."""
    app.add_exception_handler(AuthError, auth_exception_handler)
