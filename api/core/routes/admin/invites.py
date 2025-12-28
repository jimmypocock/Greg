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

from api.admin import (
    InviteCreateRequest,
    InviteDetail,
    InviteListResponse,
    InviteResponse,
    InviteService,
    MessageResponse,
)
from api.auth import AdminUser
from api.database import get_session_dependency

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
        invites=[
            InviteDetail(
                code=invite.code,
                email=invite.email,
                is_active=invite.is_active,
                created_at=invite.created_at,
                expires_at=invite.expires_at,
                used_at=invite.used_at,
                used_by=invite.used_by,
                created_by=invite.created_by,
            )
            for invite in invites
        ],
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

    return InviteResponse(
        invite=InviteDetail(
            code=invite.code,
            email=invite.email,
            is_active=invite.is_active,
            created_at=invite.created_at,
            expires_at=invite.expires_at,
            used_at=invite.used_at,
            used_by=invite.used_by,
            created_by=invite.created_by,
        ),
        signup_url=f"/auth/signup?invite={invite.code}",
    )


@router.delete("/{code}", response_model=MessageResponse)
async def revoke_invite(
    code: str,
    admin: AdminUser,
    service: Annotated[InviteService, Depends(get_invite_service)],
):
    """Revoke an invite code."""
    await service.revoke(code, admin.id)

    return MessageResponse(message=f"Invite {code} revoked")
