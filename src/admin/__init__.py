"""
Admin management module.

Provides service, schemas, exceptions, and handlers for admin endpoints.
"""

from src.admin.exceptions import (
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
from src.admin.handlers import register_admin_exception_handlers
from src.admin.schemas import (
    InviteCreateRequest,
    InviteListResponse,
    InviteResponse,
    MessageResponse,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from src.admin.service import AdminService, get_admin_service

__all__ = [
    # Exceptions
    "AdminError",
    "CannotDeleteSelfError",
    "CannotDemoteSelfError",
    "CannotDisableSelfError",
    "InvalidRoleError",
    "InviteAlreadyUsedError",
    "InviteGenerationError",
    "InviteNotFoundError",
    "UserNotFoundError",
    # Handlers
    "register_admin_exception_handlers",
    # Schemas
    "InviteCreateRequest",
    "InviteListResponse",
    "InviteResponse",
    "MessageResponse",
    "UserListResponse",
    "UserResponse",
    "UserUpdateRequest",
    # Service
    "AdminService",
    "get_admin_service",
]
