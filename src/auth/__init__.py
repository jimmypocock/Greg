"""
Authentication module.

Uses FastAPI-Users for core authentication with custom extensions for:
- API key authentication
- Invite code registration
- Role-based authorization
- Database-backed refresh tokens
"""

from src.auth.tokens import (
    generate_api_key,
    generate_invite_code,
    hash_token,
)
from src.auth.dependencies import (
    AdminUser,
    CurrentUser,
    OptionalUser,
    get_current_user_with_api_key,
    get_current_user_optional_with_api_key,
    require_admin,
)
from src.auth.users import (
    auth_backend,
    current_active_user,
    current_superuser,
    current_verified_user,
    fastapi_users,
    get_jwt_strategy,
    get_user_manager,
    optional_current_user,
    UserManager,
)
from src.auth.schemas import (
    UserCreate,
    UserRead,
    UserUpdate,
)
from src.auth.refresh_tokens import (
    create_refresh_token,
    validate_refresh_token,
    rotate_refresh_token,
    revoke_refresh_token,
    revoke_all_user_tokens,
    get_user_sessions,
    cleanup_expired_tokens,
)

__all__ = [
    # Token utilities
    "hash_token",
    "generate_api_key",
    "generate_invite_code",
    # Dependencies (with API key support)
    "get_current_user_with_api_key",
    "get_current_user_optional_with_api_key",
    "require_admin",
    # Type aliases
    "CurrentUser",
    "OptionalUser",
    "AdminUser",
    # FastAPI-Users
    "fastapi_users",
    "auth_backend",
    "current_active_user",
    "current_superuser",
    "current_verified_user",
    "optional_current_user",
    "get_jwt_strategy",
    "get_user_manager",
    "UserManager",
    # Schemas
    "UserCreate",
    "UserRead",
    "UserUpdate",
    # Refresh tokens
    "create_refresh_token",
    "validate_refresh_token",
    "rotate_refresh_token",
    "revoke_refresh_token",
    "revoke_all_user_tokens",
    "get_user_sessions",
    "cleanup_expired_tokens",
]
