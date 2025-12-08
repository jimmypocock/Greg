"""
Storage module.

Provides schemas, exceptions, handlers, and service for vector store statistics.
"""

from src.storage.exceptions import StorageError, StorageStatsError
from src.storage.handlers import register_storage_exception_handlers
from src.storage.schemas import StorageStatsResponse
from src.storage.service import StorageService

__all__ = [
    # Exceptions
    "StorageError",
    "StorageStatsError",
    # Handlers
    "register_storage_exception_handlers",
    # Schemas
    "StorageStatsResponse",
    # Service
    "StorageService",
]
