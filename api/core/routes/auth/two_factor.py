"""
Two-factor authentication routes.

Provides endpoints for setting up and managing TOTP 2FA.

Endpoints:
    GET  /auth/2fa/status   - Check if 2FA is enabled
    POST /auth/2fa/setup    - Generate TOTP secret and QR code
    POST /auth/2fa/enable   - Verify code and enable 2FA
    POST /auth/2fa/disable  - Disable 2FA (requires password)
    POST /auth/2fa/verify   - Verify TOTP code during login
"""

import base64
import io
import logging
import uuid
from typing import Annotated, Any

import jwt
import pyotp
import qrcode
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.rate_limit import limiter
from api.auth import CurrentUser
from api.auth.refresh_tokens import create_refresh_token
from api.auth.users import UserManager, get_jwt_strategy, get_user_manager, SECRET_KEY
from api.config import Config
from api.database import User, get_session_dependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/2fa", tags=["Auth - 2FA"])

TOTP_ISSUER = getattr(Config, "TOTP_ISSUER_NAME", "Songwriter")


# Request/Response schemas

class TwoFactorStatusResponse(BaseModel):
    """2FA status response."""
    enabled: bool


class TwoFactorSetupResponse(BaseModel):
    """2FA setup response with QR code."""
    secret: str
    qr_code: str  # Base64 encoded PNG
    otpauth_uri: str


class TwoFactorEnableRequest(BaseModel):
    """Request to enable 2FA."""
    code: str


class TwoFactorDisableRequest(BaseModel):
    """Request to disable 2FA."""
    password: str
    code: str


class TwoFactorVerifyRequest(BaseModel):
    """Request to verify 2FA code during login."""
    temp_token: str
    code: str


class TwoFactorVerifyResponse(BaseModel):
    """Response after successful 2FA verification."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


# Routes

@router.get("/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(user: CurrentUser):
    """Check if 2FA is enabled for the current user."""
    return TwoFactorStatusResponse(enabled=user.totp_enabled)


@router.post("/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Generate a new TOTP secret and QR code.

    This does NOT enable 2FA yet - call /enable with a valid code to activate.
    """
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled. Disable it first to set up again.",
        )

    # Generate new secret
    secret = pyotp.random_base32()

    # Create TOTP and provisioning URI
    totp = pyotp.TOTP(secret)
    otpauth_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name=TOTP_ISSUER,
    )

    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(otpauth_uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()

    # Store secret temporarily (not enabled yet)
    user.totp_secret = secret
    session.add(user)
    await session.commit()

    logger.info(f"2FA setup initiated for user {user.email}")

    return TwoFactorSetupResponse(
        secret=secret,
        qr_code=f"data:image/png;base64,{qr_base64}",
        otpauth_uri=otpauth_uri,
    )


@router.post("/enable", response_model=MessageResponse)
async def enable_2fa(
    request: TwoFactorEnableRequest,
    user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Enable 2FA by verifying a TOTP code.

    Must call /setup first to generate a secret.
    """
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled.",
        )

    if not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Call /setup first to generate a secret.",
        )

    # Verify the code
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(request.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code. Please try again.",
        )

    # Enable 2FA
    user.totp_enabled = True
    session.add(user)
    await session.commit()

    logger.info(f"2FA enabled for user {user.email}")

    return MessageResponse(message="Two-factor authentication enabled successfully.")


@router.post("/disable", response_model=MessageResponse)
async def disable_2fa(
    request: TwoFactorDisableRequest,
    user: CurrentUser,
    user_manager: Annotated[UserManager, Depends(get_user_manager)],
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Disable 2FA.

    Requires password and a valid TOTP code for security.
    """
    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled.",
        )

    # Verify password
    verified, _ = user_manager.password_helper.verify_and_update(
        request.password, user.hashed_password
    )
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid password.",
        )

    # Verify TOTP code
    if user.totp_secret:
        totp = pyotp.TOTP(user.totp_secret)
        if not totp.verify(request.code, valid_window=1):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification code.",
            )

    # Disable 2FA
    user.totp_enabled = False
    user.totp_secret = None
    session.add(user)
    await session.commit()

    logger.info(f"2FA disabled for user {user.email}")

    return MessageResponse(message="Two-factor authentication disabled.")


@router.post("/verify", response_model=TwoFactorVerifyResponse)
@limiter.limit("10/minute")
async def verify_2fa(
    request: Request,
    verify_request: TwoFactorVerifyRequest,
    session: Annotated[AsyncSession, Depends(get_session_dependency)],
):
    """
    Verify TOTP code and complete login.

    Called after /auth/token returns requires_2fa=True.
    Requires the temp_token from that response plus a valid TOTP code.
    """
    # Decode and validate the temp token
    try:
        payload = jwt.decode(
            verify_request.temp_token,
            SECRET_KEY,
            algorithms=["HS256"],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Temp token has expired. Please login again.",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid temp token.",
        )

    # Validate token type
    if payload.get("type") != "2fa_temp":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type.",
        )

    # Get the user
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload.",
        )

    result = await session.execute(
        select(User).where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled.",
        )

    if not user.totp_enabled or not user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled for this user.",
        )

    # Verify the TOTP code
    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(verify_request.code, valid_window=1):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code.",
        )

    # Generate real tokens
    jwt_strategy = get_jwt_strategy()
    access_token = await jwt_strategy.write_token(user)

    device_info = _get_device_info(request)
    refresh_token_plain, _ = await create_refresh_token(
        session,
        user,
        device_info=device_info,
    )

    logger.info(f"2FA verified for user {user.email}")

    return TwoFactorVerifyResponse(
        access_token=access_token,
        refresh_token=refresh_token_plain,
    )


# Private functions


def _get_device_info(request: Request) -> dict[str, Any]:
    """Extract device info from request for session tracking."""
    return {
        "ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
    }
