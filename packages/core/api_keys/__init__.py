"""
API key management module.

Provides service, schemas, exceptions, and handlers for API key endpoints.
"""

from packages.core.api_keys.exceptions import APIKeyError, APIKeyNotFoundError
from packages.core.api_keys.handlers import register_api_key_exception_handlers
from packages.core.api_keys.schemas import (
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyListResponse,
    APIKeyResponse,
)
from packages.core.api_keys.service import APIKeyResult, APIKeyService, get_api_key_service

__all__ = [
    # Exceptions
    "APIKeyError",
    "APIKeyNotFoundError",
    # Handlers
    "register_api_key_exception_handlers",
    # Schemas
    "APIKeyCreateRequest",
    "APIKeyCreateResponse",
    "APIKeyListResponse",
    "APIKeyResponse",
    # Service
    "APIKeyResult",
    "APIKeyService",
    "get_api_key_service",
]
