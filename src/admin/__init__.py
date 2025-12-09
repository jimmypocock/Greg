"""
Admin management module.

Provides services, schemas, exceptions, and handlers for admin endpoints.
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
from src.admin.invite_service import InviteService
from src.admin.schemas import (
    InviteCreateRequest,
    InviteListResponse,
    InviteResponse,
    MessageResponse,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from src.admin.user_service import UserService

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
