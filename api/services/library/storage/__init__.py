"""
Storage module.

Provides schemas, exceptions, handlers, and service for vector store statistics.
"""

from api.services.library.storage.exceptions import StorageError, StorageStatsError
from api.services.library.storage.handlers import register_storage_exception_handlers
from api.services.library.storage.schemas import StorageStatsResponse
from api.services.library.storage.service import StorageService

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
