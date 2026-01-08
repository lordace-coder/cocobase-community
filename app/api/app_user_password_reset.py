from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_project
from app.models.user import User
from app.schemas.projects import Project
from schemas.forgot_password import ForgotPasswordRequest, ResetPasswordRequest
from services.auth_service import AuthService
from services.email_service import EmailService
from models import AppUser
from core.database import get_db

router = APIRouter(prefix="/auth-collections", tags=["Reset-Password"])


@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
):
    """
    Send password reset email to user.
    Always returns 200 to prevent email enumeration.
    """
    email_service = EmailService(project=proj[0], db=db)

    user = db.query(AppUser).filter(AppUser.email == request.email).first()

    if user:
        token = AuthService.create_reset_token(db, user.id)
        await email_service.send_email(user.email, token)

    # Always return success to prevent email enumeration
    return {"message": "If that email exists, a reset link has been sent"}


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(request: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Reset password using valid token."""
    reset_token = AuthService.verify_reset_token(db, request.token)

    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Update user password
    user = db.query(AppUser).filter(AppUser.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="AppUser not found"
        )

    user.set_password(request.new_password)

    # Mark token as used
    reset_token.is_used = True

    db.commit()
    return {"message": "Password successfully reset"}
