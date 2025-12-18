"""
Authentication middleware for setting user in request state.

This middleware extracts the user from JWT tokens and sets it in
request.state for use by rate limiting and other middleware.
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from packages.core.auth.users import get_jwt_strategy

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware that extracts user from JWT and sets in request.state.

    This allows rate limiting and other middleware to access the user
    before route handlers run.
    """

    async def dispatch(self, request: Request, call_next):
        # Try to extract user from Authorization header
        auth_header = request.headers.get("Authorization")

        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header[7:]  # Remove "Bearer " prefix
            try:
                user = await self._get_user_from_token(token, request)
                if user:
                    request.state.user = user
            except Exception as e:
                # Log but don't fail - let the route handler deal with auth
                logger.debug(f"Auth middleware: could not extract user: {e}")

        response = await call_next(request)
        return response

    async def _get_user_from_token(self, token: str, request: Request):
        """Extract user from JWT token."""
        from packages.core.database import async_session_factory
        from packages.core.auth.users import get_user_manager

        try:
            jwt_strategy = get_jwt_strategy()

            async with async_session_factory() as session:
                user_manager = get_user_manager(session)
                user = await jwt_strategy.read_token(token, user_manager)
                return user
        except Exception:
            return None
