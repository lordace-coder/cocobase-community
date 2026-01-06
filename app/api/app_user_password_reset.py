from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from schemas.forgot_password import ForgotPasswordRequest, ResetPasswordRequest
from services.auth_service import AuthService
from services.email_service import EmailService
from models import AppUser
from core.database import get_db

router = APIRouter(prefix="/auth", tags=["Reset-Password"])
email_service = EmailService()

@router.post("/forgot-password", status_code=status.HTTP_200_OK)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db)
):
    """
    Send password reset email to user.
    Always returns 200 to prevent email enumeration.
    """
    user = db.query(AppUser).filter(AppUser.email == request.email).first()
    
    if user :
        token = AuthService.create_reset_token(db, user.id)
        await email_service.send_reset_email(user.email, token)
    
    # Always return success to prevent email enumeration
    return {
        "message": "If that email exists, a reset link has been sent"
    }

@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(get_db)
):
    """Reset password using valid token."""
    reset_token = AuthService.verify_reset_token(db, request.token)
    
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Update user password
    user = db.query(AppUser).filter(AppUser.id == reset_token.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AppUser not found"
        )
    
    user.set_password(request.new_password)
    
    # Mark token as used
    reset_token.is_used = True
    
    db.commit()
    return {"message": "Password successfully reset"}

