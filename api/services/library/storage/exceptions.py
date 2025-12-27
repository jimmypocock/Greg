"""
Storage module exceptions.

Domain-specific exceptions for storage operations.
"""


class StorageError(Exception):
    """Base exception for storage errors."""

    def __init__(self, message: str = "Storage error"):
        self.message = message
        super().__init__(self.message)


class StorageStatsError(StorageError):
    """Raised when fetching storage stats fails."""

    def __init__(self):
        super().__init__("Failed to get storage stats")
