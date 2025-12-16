"""
Session management routes.

Provides endpoints for viewing and managing user sessions.

Endpoints:
    GET    /auth/sessions        - List active sessions
    DELETE /auth/sessions/{id}   - Revoke specific session
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.auth import CurrentUser
from packages.core.auth.refresh_tokens import get_active_refresh_tokens, revoke_user_session
from packages.core.auth.schemas import MessageResponse, SessionListResponse, SessionResponse
from packages.core.database import get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter()


# Routes


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """List all active sessions for the current user."""
    tokens = await get_active_refresh_tokens(session, user.id)

    return SessionListResponse(
        sessions=[SessionResponse.from_model(t) for t in tokens],
        count=len(tokens),
    )


@router.delete("/{session_id}", response_model=MessageResponse)
async def revoke_session(
    session_id: str,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """Revoke a specific session by ID."""
    await revoke_user_session(session, session_id, user.id)

    logger.info(f"User {user.email} revoked session {session_id}")

    return MessageResponse(message="Session revoked")
