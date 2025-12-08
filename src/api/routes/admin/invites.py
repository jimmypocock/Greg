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

from src.admin import (
    AdminService,
    InviteCreateRequest,
    InviteListResponse,
    InviteResponse,
    MessageResponse,
)
from src.auth import AdminUser
from src.database import get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter()


# Dependencies


async def get_admin_service(
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
) -> AdminService:
    """Get admin service with session."""
    return AdminService(session=session)


# Routes


@router.get("", response_model=InviteListResponse)
async def list_invites(
    admin: AdminUser,
    service: Annotated[AdminService, Depends(get_admin_service)],
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    active: bool | None = None,
    used: bool | None = None,
):
    """List all invites with optional filtering."""
    invites, total = await service.list_invites(skip, limit, active, used)

    return InviteListResponse(
        invites=[invite.to_dict() for invite in invites],
        total=total,
    )


@router.post("", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    request: InviteCreateRequest,
    admin: AdminUser,
    service: Annotated[AdminService, Depends(get_admin_service)],
):
    """Create a new invite code."""
    invite = await service.create_invite(admin.id, request)

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
    service: Annotated[AdminService, Depends(get_admin_service)],
):
    """Revoke an invite code."""
    await service.delete_invite(code)

    logger.info(f"Admin {admin.email} revoked invite {code}")

    return MessageResponse(message=f"Invite {code} revoked")
