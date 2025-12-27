"""
Authentication module.

Uses FastAPI-Users for core authentication with custom extensions for:
- API key authentication
- Database-backed refresh tokens
- Invite code registration
- Role-based authorization
"""

from api.auth.dependencies import (
    AdminAuth,
    AdminUser,
    Auth,
    AuthContext,
    CurrentUser,
    MaybeAuth,
    get_auth_context,
    get_auth_context_optional,
    get_current_user_with_api_key,
    require_admin,
)
from api.auth.exceptions import (
    AuthError,
    EmailAlreadyExistsError,
    ExpiredTokenError,
    InvalidCredentialsError,
    InvalidInviteCodeError,
    InvalidSessionIdError,
    InvalidTokenError,
    RevokedTokenError,
    SessionAlreadyRevokedError,
    SessionNotFoundError,
    UserDisabledError,
    UserNotFoundError,
)
from api.auth.handlers import register_auth_exception_handlers
from api.auth.internal_api import (
    INTERNAL_API_KEY_HEADER,
    RequireInternalOrAdmin,
    check_internal_api_key,
    require_internal_api_key,
)
from api.auth.middleware import AuthMiddleware
from api.auth.refresh_tokens import (
    cleanup_expired_tokens,
    create_refresh_token,
    get_active_refresh_tokens,
    revoke_all_user_tokens,
    revoke_refresh_token,
    revoke_user_session,
    rotate_refresh_token,
    validate_refresh_token,
)
from api.auth.schemas import (
    UserCreate,
    UserRead,
    UserUpdate,
)
from api.auth.tokens import (
    generate_api_key,
    generate_invite_code,
    hash_token,
)
from api.auth.users import (
    UserManager,
    auth_backend,
    current_active_user,
    current_superuser,
    current_verified_user,
    fastapi_users,
    get_jwt_strategy,
    get_user_manager,
    optional_current_user,
)

__all__ = [
    # Auth context
    "AdminAuth",
    "Auth",
    "AuthContext",
    "MaybeAuth",
    "get_auth_context",
    "get_auth_context_optional",
    "require_admin",
    # Exceptions
    "AuthError",
    "EmailAlreadyExistsError",
    "ExpiredTokenError",
    "InvalidCredentialsError",
    "InvalidInviteCodeError",
    "InvalidSessionIdError",
    "InvalidTokenError",
    "RevokedTokenError",
    "SessionAlreadyRevokedError",
    "SessionNotFoundError",
    "UserDisabledError",
    "UserNotFoundError",
    # Exception handlers
    "register_auth_exception_handlers",
    # Middleware
    "AuthMiddleware",
    # Internal API key
    "INTERNAL_API_KEY_HEADER",
    "RequireInternalOrAdmin",
    "check_internal_api_key",
    "require_internal_api_key",
    # FastAPI-Users
    "UserManager",
    "auth_backend",
    "current_active_user",
    "current_superuser",
    "current_verified_user",
    "fastapi_users",
    "get_jwt_strategy",
    "get_user_manager",
    "optional_current_user",
    # User-only dependencies
    "AdminUser",
    "CurrentUser",
    "get_current_user_with_api_key",
    # Refresh tokens
    "cleanup_expired_tokens",
    "create_refresh_token",
    "get_active_refresh_tokens",
    "revoke_all_user_tokens",
    "revoke_refresh_token",
    "revoke_user_session",
    "rotate_refresh_token",
    "validate_refresh_token",
    # Schemas
    "UserCreate",
    "UserRead",
    "UserUpdate",
    # Token utilities
    "generate_api_key",
    "generate_invite_code",
    "hash_token",
]
