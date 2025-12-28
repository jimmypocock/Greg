"""
User management routes (FastAPI-Users).

Provides user profile management endpoints from FastAPI-Users.

Endpoints:
    GET    /auth/users/me    - Get current user (from fastapi-users)
    PATCH  /auth/users/me    - Update current user (from fastapi-users)
    GET    /auth/users/{id}  - Get user by ID (from fastapi-users)
    PATCH  /auth/users/{id}  - Update user by ID (from fastapi-users)
    DELETE /auth/users/{id}  - Delete user by ID (from fastapi-users)
"""

from api.auth.schemas import UserRead, UserUpdate
from api.auth.users import fastapi_users

router = fastapi_users.get_users_router(UserRead, UserUpdate)
