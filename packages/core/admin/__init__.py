"""
Admin management module.

Provides services, schemas, exceptions, and handlers for admin endpoints.
"""

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
from packages.core.admin.handlers import register_admin_exception_handlers
from packages.core.admin.invite_service import InviteService
from packages.core.admin.schemas import (
    InviteCreateRequest,
    InviteListResponse,
    InviteResponse,
    MessageResponse,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from packages.core.admin.user_service import UserService

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
    # Services
    "InviteService",
    "UserService",
]
