"""
Admin invite management routes.

Provides admin-only endpoints for invite code management.

Endpoints:
    GET    /admin/invites            - List all invites
    POST   /admin/invites            - Create invite
    DELETE /admin/invites/{code}     - Revoke invite
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from packages.core.admin import (
    InviteCreateRequest,
    InviteListResponse,
    InviteResponse,
    InviteService,
    MessageResponse,
)
from packages.core.auth import AdminUser
from packages.core.database import get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependencies


async def get_invite_service(
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
) -> InviteService:
    """Get invite service with session."""
    return InviteService(session=session)


# Routes


@router.get("", response_model=InviteListResponse)
async def list_invites(
    admin: AdminUser,
    service: Annotated[InviteService, Depends(get_invite_service)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    active: bool | None = None,
    used: bool | None = None,
):
    """List all invites with optional filtering."""
    invites, total = await service.list(skip, limit, active, used)

    return InviteListResponse(
        invites=[invite.to_dict() for invite in invites],
        total=total,
    )


@router.post("", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    request: InviteCreateRequest,
    admin: AdminUser,
    service: Annotated[InviteService, Depends(get_invite_service)],
):
    """Create a new invite code."""
    invite = await service.create(admin.id, request)

    logger.info(f"Admin {admin.email} created invite {invite.code}")

    return InviteResponse(
        code=invite.code,
        signup_url=f"/auth/signup?invite={invite.code}",
        email=request.email,
        expires_at=invite.expires_at.isoformat() if invite.expires_at else None,
    )


@router.delete("/{code}", response_model=MessageResponse)
async def delete_invite(
    code: str,
    admin: AdminUser,
    service: Annotated[InviteService, Depends(get_invite_service)],
):
    """Revoke an invite code."""
    await service.delete(code)

    logger.info(f"Admin {admin.email} revoked invite {code}")

    return MessageResponse(message=f"Invite {code} revoked")
