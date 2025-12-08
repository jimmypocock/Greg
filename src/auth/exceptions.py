"""
Authentication exceptions.

Domain-specific exceptions for auth operations. These are converted
to HTTP responses by exception handlers in the API layer.
"""


# Base exception


class AuthError(Exception):
    """Base exception for authentication errors."""

    def __init__(self, message: str = "Authentication error"):
        self.message = message
        super().__init__(self.message)


# Authentication exceptions


class InvalidCredentialsError(AuthError):
    """Raised when email/password combination is invalid."""

    def __init__(self):
        super().__init__("Invalid email or password")


class UserDisabledError(AuthError):
    """Raised when user account is disabled."""

    def __init__(self):
        super().__init__("Account is disabled")


class UserNotFoundError(AuthError):
    """Raised when user is not found."""

    def __init__(self):
        super().__init__("User not found")


# Token exceptions


class InvalidTokenError(AuthError):
    """Raised when a token is invalid or malformed."""

    def __init__(self, message: str = "Invalid token"):
        super().__init__(message)


class ExpiredTokenError(AuthError):
    """Raised when a token has expired."""

    def __init__(self):
        super().__init__("Token has expired")


class RevokedTokenError(AuthError):
    """Raised when a token has been revoked."""

    def __init__(self):
        super().__init__("Token has been revoked")


# Registration exceptions


class InvalidInviteCodeError(AuthError):
    """Raised when invite code is invalid or expired."""

    def __init__(self):
        super().__init__("Invalid or expired invite code")


class EmailAlreadyExistsError(AuthError):
    """Raised when email is already registered."""

    def __init__(self):
        super().__init__("Email already registered")


# Session exceptions


class SessionNotFoundError(AuthError):
    """Raised when session is not found."""

    def __init__(self):
        super().__init__("Session not found")


class SessionAlreadyRevokedError(AuthError):
    """Raised when session is already revoked."""

    def __init__(self):
        super().__init__("Session already revoked")


class InvalidSessionIdError(AuthError):
    """Raised when session ID format is invalid."""

    def __init__(self):
        super().__init__("Invalid session ID format")
