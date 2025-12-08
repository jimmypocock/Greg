"""
API key module exceptions.

Domain-specific exceptions for API key operations.
"""


class APIKeyError(Exception):
    """Base exception for API key errors."""

    def __init__(self, message: str = "API key error"):
        self.message = message
        super().__init__(self.message)


class APIKeyNotFoundError(APIKeyError):
    """Raised when API key is not found."""

    def __init__(self, key_id: str | None = None):
        msg = f"API key {key_id} not found" if key_id else "API key not found"
        super().__init__(msg)
