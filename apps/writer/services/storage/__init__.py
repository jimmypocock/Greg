"""
Storage module.

Provides schemas, exceptions, handlers, and service for vector store statistics.
"""

from apps.writer.services.storage.exceptions import StorageError, StorageStatsError
from apps.writer.services.storage.handlers import register_storage_exception_handlers
from apps.writer.services.storage.schemas import StorageStatsResponse
from apps.writer.services.storage.service import StorageService

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
