"""
Authentication module.

Uses FastAPI-Users for core authentication with custom extensions for:
- API key authentication
- Database-backed refresh tokens
- Invite code registration
- Role-based authorization
"""

from src.auth.dependencies import (
    AdminAuth,
    AdminUser,
    Auth,
    AuthContext,
    CurrentUser,
    MaybeAuth,
    OptionalUser,
    get_auth_context,
    get_auth_context_optional,
    get_current_user_optional_with_api_key,
    get_current_user_with_api_key,
    require_admin,
)
from src.auth.refresh_tokens import (
    cleanup_expired_tokens,
    create_refresh_token,
    get_active_refresh_tokens,
    revoke_all_user_tokens,
    revoke_refresh_token,
    rotate_refresh_token,
    validate_refresh_token,
)
from src.auth.schemas import (
    UserCreate,
    UserRead,
    UserUpdate,
)
from src.auth.tokens import (
    generate_api_key,
    generate_invite_code,
    hash_token,
)
from src.auth.users import (
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
    # Legacy dependencies
    "AdminUser",
    "CurrentUser",
    "OptionalUser",
    "get_current_user_optional_with_api_key",
    "get_current_user_with_api_key",
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
    # Refresh tokens
    "cleanup_expired_tokens",
    "create_refresh_token",
    "get_active_refresh_tokens",
    "revoke_all_user_tokens",
    "revoke_refresh_token",
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
