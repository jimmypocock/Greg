"""
Admin management module.

Provides services, schemas, exceptions, and handlers for admin endpoints.
"""

from api.admin.exceptions import (
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
from api.admin.handlers import register_admin_exception_handlers
from api.admin.invite_service import InviteService
from api.admin.schemas import (
    InviteCreateRequest,
    InviteDetail,
    InviteListResponse,
    InviteResponse,
    MessageResponse,
    UserDetail,
    UserListResponse,
    UserResponse,
    UserUpdateRequest,
)
from api.admin.user_service import UserService

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
    "InviteDetail",
    "InviteListResponse",
    "InviteResponse",
    "MessageResponse",
    "UserDetail",
    "UserListResponse",
    "UserResponse",
    "UserUpdateRequest",
    # Services
    "InviteService",
    "UserService",
]
