"""
Current user profile routes.

Provides endpoints for the current authenticated user.

Endpoints:
    GET    /auth/me            - Get current user info
    POST   /auth/me/password   - Change password
    DELETE /auth/me            - Deactivate account (soft delete)
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.api.rate_limit import limiter
from api.auth import CurrentUser
from api.auth.refresh_tokens import revoke_all_user_tokens
from api.auth.schemas import DeactivateAccountRequest, MessageResponse, PasswordChangeRequest, UserRead
from api.auth.users import UserManager, get_user_manager
from api.billing import StripeService, is_stripe_configured
from api.database import get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter()


# Routes


@router.get("/me", response_model=UserRead)
async def get_current_user_info(user: CurrentUser):
    """Get the current authenticated user's info."""
    return user


@router.post("/me/password", response_model=MessageResponse)
@limiter.limit("5/minute")
async def change_password(
    request: Request,
    password_request: PasswordChangeRequest,
    user: CurrentUser,
    user_manager: Annotated[UserManager, Depends(get_user_manager)],
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Change the current user's password.

    Requires the current password for verification.
    """
    # Verify current password
    verified, _ = user_manager.password_helper.verify_and_update(
        password_request.current_password, user.hashed_password
    )
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    # Hash new password and update
    user.hashed_password = user_manager.password_helper.hash(password_request.new_password)
    session.add(user)
    await session.commit()

    logger.info(f"Password changed for user {user.email}")

    return MessageResponse(message="Password changed successfully.")


@router.delete("/me", response_model=MessageResponse)
@limiter.limit("3/minute")
async def deactivate_account(
    request: Request,
    deactivate_request: DeactivateAccountRequest,
    user: CurrentUser,
    user_manager: Annotated[UserManager, Depends(get_user_manager)],
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Deactivate (soft delete) the current user's account.

    This will:
    - Set account as inactive (soft delete)
    - Anonymize the email address
    - Cancel any active Stripe subscription
    - Revoke all active sessions

    The account data is retained but the user cannot login.
    Requires password confirmation and typing 'DELETE'.
    """
    # Verify password
    verified, _ = user_manager.password_helper.verify_and_update(
        deactivate_request.password, user.hashed_password
    )
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password is incorrect.",
        )

    original_email = user.email

    # Cancel Stripe subscription if exists
    if is_stripe_configured() and user.stripe_subscription_id:
        try:
            stripe_service = StripeService(session)
            await stripe_service.cancel_subscription(user.id)
            logger.info(f"Cancelled Stripe subscription for deactivated user {original_email}")
        except Exception as e:
            logger.warning(f"Failed to cancel subscription during deactivation: {e}")

    # Revoke all sessions
    await revoke_all_user_tokens(session, user.id)

    # Anonymize and deactivate
    # Use a unique suffix to avoid conflicts if email is reused
    deletion_suffix = uuid.uuid4().hex[:8]
    user.email = f"deleted_{deletion_suffix}@deactivated.local"
    user.is_active = False
    user.is_verified = False

    # Clear sensitive fields
    user.stripe_customer_id = None
    user.stripe_subscription_id = None
    user.totp_secret = None
    user.totp_enabled = False

    session.add(user)
    await session.commit()

    logger.info(f"Account deactivated for user {original_email}")

    return MessageResponse(
        message="Your account has been deactivated. All your data has been retained but anonymized."
    )
