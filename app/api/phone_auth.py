"""
Phone Authentication API

Handles phone number verification, login with phone, and secure phone number updates.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel
from typing import Optional

from app.core.database import get_db
from app.core.dependencies import get_project, get_app_user
from app.models.app_client import AppUser, Project
from app.models.user import User
from app.models.two_factor_auth import TwoFactorCode, TwoFactorSettings
from app.services.jwt import create_app_user_token

router = APIRouter(prefix="/auth-collections/phone", tags=["Phone Authentication"])


# =========================
# REQUEST/RESPONSE MODELS
# =========================

class SendPhoneOTPRequest(BaseModel):
    """Request to send OTP to phone number"""
    phone_number: str


class VerifyPhoneOTPRequest(BaseModel):
    """Request to verify phone OTP"""
    phone_number: str
    code: str


class PhoneLoginRequest(BaseModel):
    """Request to login with phone number"""
    phone_number: str
    code: str


class UpdatePhoneRequest(BaseModel):
    """Request to update phone number (requires password verification)"""
    new_phone_number: str
    password: str


class PhoneOTPResponse(BaseModel):
    """Response containing OTP details for SMS sending"""
    message: str
    phone_number: str
    code: str  # You'll send this via SMS
    expires_in_minutes: int


# =========================
# HELPER FUNCTIONS
# =========================

def check_phone_login_enabled(project: Project) -> bool:
    """Check if phone login is enabled at project level"""
    if not project.configs:
        return False
    return project.configs.get('ENABLE_PHONE_LOGIN', False)


def generate_phone_otp(db: Session, user_id: str, project_id: str, project: Project) -> tuple[str, int]:
    """Generate OTP for phone verification"""
    # Get OTP length from project config
    otp_length = 6
    if project.configs:
        otp_length = project.configs.get('OTP_LENGTH', 6)
        otp_length = max(4, min(10, otp_length))

    code = TwoFactorCode.generate_code(length=otp_length)
    expiry_minutes = 10

    # Store the OTP (reusing TwoFactorCode table)
    otp = TwoFactorCode(
        user_id=user_id,
        project_id=project_id,
        code=code,
        expires_at=datetime.utcnow() + timedelta(minutes=expiry_minutes)
    )
    db.add(otp)
    db.commit()

    return code, expiry_minutes


def check_rate_limit(db: Session, user_id: str, project_id: str) -> bool:
    """Check if user has exceeded OTP rate limit"""
    recent_codes = db.query(TwoFactorCode).filter(
        TwoFactorCode.user_id == user_id,
        TwoFactorCode.project_id == project_id,
        TwoFactorCode.created_at >= datetime.utcnow() - timedelta(minutes=15)
    ).count()

    return recent_codes <= 10


# =========================
# PHONE VERIFICATION ROUTES
# =========================

@router.post("/send-otp", response_model=PhoneOTPResponse)
async def send_phone_otp(
    request: SendPhoneOTPRequest,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
    user: AppUser = Depends(get_app_user),
):
    """
    Send OTP to phone number for verification.

    User must be authenticated. Returns the OTP code for you to send via SMS.
    """
    if not user:
        raise HTTPException(401, "Authentication required")

    project = proj[0]

    # Rate limiting
    if not check_rate_limit(db, user.id, project.id):
        raise HTTPException(429, "Too many OTP requests. Please try again later.")

    # Check for existing pending code
    existing_code = db.query(TwoFactorCode).filter(
        TwoFactorCode.user_id == user.id,
        TwoFactorCode.project_id == project.id,
        TwoFactorCode.is_used == False,
        TwoFactorCode.created_at >= datetime.utcnow() - timedelta(minutes=2)
    ).order_by(TwoFactorCode.created_at.desc()).first()

    if existing_code and existing_code.is_valid():
        return PhoneOTPResponse(
            message="OTP already sent. Please wait before requesting a new one.",
            phone_number=request.phone_number,
            code=existing_code.code,
            expires_in_minutes=10
        )

    # Generate new OTP
    code, expiry_minutes = generate_phone_otp(db, user.id, project.id, project)

    return PhoneOTPResponse(
        message="OTP generated successfully. Send this code via SMS.",
        phone_number=request.phone_number,
        code=code,
        expires_in_minutes=expiry_minutes
    )


@router.post("/verify-otp")
async def verify_phone_otp(
    request: VerifyPhoneOTPRequest,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
    user: AppUser = Depends(get_app_user),
):
    """
    Verify phone OTP and mark phone as verified.

    User must be authenticated.
    """
    if not user:
        raise HTTPException(401, "Authentication required")

    project = proj[0]

    # Verify OTP
    otp = db.query(TwoFactorCode).filter(
        TwoFactorCode.user_id == user.id,
        TwoFactorCode.project_id == project.id,
        TwoFactorCode.code == request.code,
        TwoFactorCode.is_used == False
    ).order_by(TwoFactorCode.created_at.desc()).first()

    if not otp:
        raise HTTPException(400, "Invalid or expired OTP")

    if not otp.is_valid():
        raise HTTPException(400, "OTP has expired")

    # Mark OTP as used
    otp.is_used = True

    # Update user's phone number and verification status
    user.phone_number = request.phone_number
    user.phone_verified = True
    user.phone_verified_at = datetime.utcnow()

    db.commit()

    return {
        "message": "Phone number verified successfully",
        "phone_number": request.phone_number,
        "phone_verified": True,
        "verified_at": user.phone_verified_at.isoformat()
    }


# =========================
# PHONE LOGIN ROUTES
# =========================

@router.post("/login/send-otp", response_model=PhoneOTPResponse)
async def send_login_otp(
    request: SendPhoneOTPRequest,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
):
    """
    Send OTP for phone login.

    This is called during login flow (no authentication required).
    Returns OTP code for you to send via SMS.

    Requires ENABLE_PHONE_LOGIN to be true in project configs.
    """
    project = proj[0]

    # Check if phone login is enabled at project level
    if not check_phone_login_enabled(project):
        raise HTTPException(400, "Phone login is not enabled for this project")

    # Find user by phone number
    user = db.query(AppUser).filter(
        AppUser.phone_number == request.phone_number,
        AppUser.client_id == project.id
    ).first()

    if not user:
        raise HTTPException(404, "No account found with this phone number")

    # Rate limiting
    if not check_rate_limit(db, user.id, project.id):
        raise HTTPException(429, "Too many OTP requests. Please try again later.")

    # Check for existing pending code
    existing_code = db.query(TwoFactorCode).filter(
        TwoFactorCode.user_id == user.id,
        TwoFactorCode.project_id == project.id,
        TwoFactorCode.is_used == False,
        TwoFactorCode.created_at >= datetime.utcnow() - timedelta(minutes=2)
    ).order_by(TwoFactorCode.created_at.desc()).first()

    if existing_code and existing_code.is_valid():
        return PhoneOTPResponse(
            message="OTP already sent. Please wait before requesting a new one.",
            phone_number=request.phone_number,
            code=existing_code.code,
            expires_in_minutes=10
        )

    # Generate new OTP
    code, expiry_minutes = generate_phone_otp(db, user.id, project.id, project)

    return PhoneOTPResponse(
        message="OTP generated successfully. Send this code via SMS.",
        phone_number=request.phone_number,
        code=code,
        expires_in_minutes=expiry_minutes
    )


@router.post("/login")
async def login_with_phone(
    request: PhoneLoginRequest,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
):
    """
    Login with phone number and OTP.

    Returns access token on successful verification.

    Requires ENABLE_PHONE_LOGIN to be true in project configs.
    """
    project = proj[0]

    # Check if phone login is enabled at project level
    if not check_phone_login_enabled(project):
        raise HTTPException(400, "Phone login is not enabled for this project")

    # Find user by phone number
    user = db.query(AppUser).filter(
        AppUser.phone_number == request.phone_number,
        AppUser.client_id == project.id
    ).first()

    if not user:
        raise HTTPException(400, "Invalid phone number or code")

    # Rate limiting
    recent_attempts = db.query(TwoFactorCode).filter(
        TwoFactorCode.user_id == user.id,
        TwoFactorCode.project_id == project.id,
        TwoFactorCode.created_at >= datetime.utcnow() - timedelta(minutes=15)
    ).count()

    if recent_attempts > 10:
        raise HTTPException(429, "Too many login attempts. Please try again later.")

    # Verify OTP
    otp = db.query(TwoFactorCode).filter(
        TwoFactorCode.user_id == user.id,
        TwoFactorCode.project_id == project.id,
        TwoFactorCode.code == request.code,
        TwoFactorCode.is_used == False
    ).order_by(TwoFactorCode.created_at.desc()).first()

    if not otp:
        raise HTTPException(400, "Invalid phone number or code")

    if not otp.is_valid():
        raise HTTPException(400, "OTP has expired")

    # Mark OTP as used
    otp.is_used = True
    db.commit()

    # Generate access token
    access_token = create_app_user_token(user)

    return {
        "access_token": access_token,
        "user": {
            "id": user.id,
            "email": user.email,
            "phone_number": user.phone_number,
            "phone_verified": user.phone_verified,
            "data": user.data or {},
            "roles": user.roles or [],
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
    }


# =========================
# PHONE SETTINGS ROUTES
# =========================

@router.get("/settings")
async def get_phone_settings(
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
    user: AppUser = Depends(get_app_user),
):
    """
    Get current phone authentication settings.
    """
    if not user:
        raise HTTPException(401, "Authentication required")

    project = proj[0]

    return {
        "phone_number": user.phone_number,
        "phone_verified": user.phone_verified,
        "phone_verified_at": user.phone_verified_at.isoformat() if user.phone_verified_at else None,
        "phone_login_enabled_for_project": check_phone_login_enabled(project)
    }


# =========================
# SECURE PHONE UPDATE ROUTE
# =========================

@router.post("/update")
async def update_phone_number(
    request: UpdatePhoneRequest,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
    user: AppUser = Depends(get_app_user),
):
    """
    Securely update phone number.

    Requires password verification for security.
    This resets phone_verified to false - user must re-verify the new number.
    """
    if not user:
        raise HTTPException(401, "Authentication required")

    # Verify password
    if not user.compare_password(request.password):
        raise HTTPException(400, "Invalid password")

    project = proj[0]

    # Check if phone number is already in use by another user in this project
    existing_user = db.query(AppUser).filter(
        AppUser.phone_number == request.new_phone_number,
        AppUser.client_id == project.id,
        AppUser.id != user.id
    ).first()

    if existing_user:
        raise HTTPException(400, "This phone number is already in use")

    # Update phone number and reset verification
    user.phone_number = request.new_phone_number
    user.phone_verified = False
    user.phone_verified_at = None

    db.commit()

    return {
        "message": "Phone number updated successfully",
        "phone_number": user.phone_number,
        "phone_verified": False
    }


@router.delete("/remove")
async def remove_phone_number(
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_app_user),
):
    """
    Remove phone number from account.
    """
    if not user:
        raise HTTPException(401, "Authentication required")

    if not user.phone_number:
        raise HTTPException(400, "No phone number to remove")

    user.phone_number = None
    user.phone_verified = False
    user.phone_verified_at = None

    db.commit()

    return {
        "message": "Phone number removed successfully"
    }
