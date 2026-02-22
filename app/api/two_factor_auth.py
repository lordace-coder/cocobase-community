from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.core.database import get_db
from app.core.dependencies import get_project, get_app_user
from app.models.two_factor_auth import TwoFactorCode, TwoFactorSettings
from app.models.app_client import AppUser, Project
from app.models.user import User
from app.services.email_service import EmailService

router = APIRouter(prefix="/auth-collections/2fa", tags=["2FA"])


class Enable2FARequest(BaseModel):
    """Request to enable 2FA - user must be authenticated"""

    pass


class Verify2FARequest(BaseModel):
    """Request to verify 2FA code"""

    email: str
    code: str


class Send2FACodeRequest(BaseModel):
    """Request to send 2FA code"""

    email: str


@router.post("/enable")
async def enable_2fa(
    request: Enable2FARequest,
    db: Session = Depends(get_db),
    proj_user: AppUser = Depends(get_app_user),
    proj: tuple[Project, User] = Depends(get_project),
):
    """
    Enable 2FA for the authenticated user.
    User must be authenticated to enable 2FA for their own account.
    """
    if not proj_user:
        raise HTTPException(401, "Authentication required")

    project = proj[0]

    # Check if 2FA is enabled for this project
    if not project.configs or not project.configs.get("ENABLE_2FA", False):
        raise HTTPException(400, "2FA is not enabled for this project")

    # Create or update 2FA settings for the authenticated user (proj_user, not the project owner)
    settings = (
        db.query(TwoFactorSettings)
        .filter(TwoFactorSettings.user_id == proj_user.id)
        .first()
    )

    if not settings:
        settings = TwoFactorSettings(
            user_id=proj_user.id, project_id=project.id, is_enabled=True
        )
        db.add(settings)
    else:
        settings.is_enabled = True

    db.commit()
    return {"message": "2FA enabled successfully"}


@router.post("/disable")
async def disable_2fa(
    db: Session = Depends(get_db),
    proj_user: AppUser = Depends(get_app_user),
):
    """
    Disable 2FA for the authenticated user.
    User must be authenticated to disable 2FA for their own account.
    """
    if not proj_user:
        raise HTTPException(401, "Authentication required")

    # Find and disable 2FA settings for the authenticated user
    settings = (
        db.query(TwoFactorSettings)
        .filter(TwoFactorSettings.user_id == proj_user.id)
        .first()
    )

    if settings:
        settings.is_enabled = False
        db.commit()
        return {"message": "2FA disabled successfully"}

    raise HTTPException(404, "2FA settings not found")


@router.post("/send-code")
async def send_2fa_code(
    request: Send2FACodeRequest,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    proj: tuple[Project, any] = Depends(get_project),
):
    """
    Send 2FA code to user's email.
    This is called during login flow, so it doesn't require user authentication.
    """
    project = proj[0]

    proj_user = (
        db.query(AppUser)
        .filter(AppUser.email == request.email, AppUser.client_id == project.id)
        .first()
    )
    # Check if 2FA is enabled for this user
    settings = (
        db.query(TwoFactorSettings)
        .filter(
            TwoFactorSettings.user_id == proj_user.id,
            TwoFactorSettings.is_enabled == True,
        )
        .first()
    )

    if not settings:
        raise HTTPException(400, "2FA is not enabled for this user")

    # Get OTP length from project config (default: 6, allowed: 4-10)
    otp_length = 6
    if project.configs:
        otp_length = project.configs.get("OTP_LENGTH", 6)
        otp_length = max(4, min(10, otp_length))  # Clamp between 4 and 10

    # Generate code
    code = TwoFactorCode.generate_code(length=otp_length)
    expiry_minutes = 10

    twofa_code = TwoFactorCode(
        user_id=proj_user.id,
        project_id=project.id,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=expiry_minutes),
    )
    db.add(twofa_code)
    db.commit()

    # Send email in background
    email_service = EmailService(project_id=project.id, db=db)
    user_name = (
        getattr(proj_user, "name", None)
        or getattr(proj_user, "username", None)
        or proj_user.email
    )

    bg.add_task(
        email_service.send_2fa_code_email,
        to_email=proj_user.email,
        code=code,
        user_name=user_name,
        app_name=project.name,
        expiry_minutes=expiry_minutes,
    )

    return {"message": "2FA code sent"}


@router.post("/verify")
async def verify_2fa_code(
    request: Verify2FARequest,
    db: Session = Depends(get_db),
    proj: tuple[Project, any] = Depends(get_project),
):
    """
    Verify 2FA code and return access token.
    This is called during login flow to complete authentication after 2FA verification.
    Uses email address instead of user_id for better UX and security.
    """
    from app.api.auth_collection import create_app_user_token

    project = proj[0]

    # Get user by email
    user = (
        db.query(AppUser)
        .filter(AppUser.email == request.email, AppUser.client_id == project.id)
        .first()
    )

    if not user:
        raise HTTPException(400, "Invalid email or code")

    # Rate limiting: Check for too many failed attempts
    recent_attempts = (
        db.query(TwoFactorCode)
        .filter(
            TwoFactorCode.user_id == user.id,
            TwoFactorCode.project_id == project.id,
            TwoFactorCode.created_at >= datetime.utcnow() - timedelta(minutes=15),
        )
        .count()
    )

    if recent_attempts > 10:
        raise HTTPException(
            429, "Too many verification attempts. Please try again later."
        )

    # Get most recent unused code for user
    twofa_code = (
        db.query(TwoFactorCode)
        .filter(
            TwoFactorCode.user_id == user.id,
            TwoFactorCode.project_id == project.id,
            TwoFactorCode.code == request.code,
            TwoFactorCode.is_used == False,
        )
        .order_by(TwoFactorCode.created_at.desc())
        .first()
    )

    if not twofa_code:
        raise HTTPException(400, "Invalid email or code")

    if not twofa_code.is_valid():
        raise HTTPException(400, "Code expired or already used")

    # Mark as used
    twofa_code.is_used = True

    # Update last verified
    settings = (
        db.query(TwoFactorSettings).filter(TwoFactorSettings.user_id == user.id).first()
    )
    if settings:
        settings.last_verified_at = datetime.utcnow()

    db.commit()

    # Return access token to complete login
    return {
        "access_token": create_app_user_token(user),
        "user": user,
        "message": "2FA verification successful",
    }
