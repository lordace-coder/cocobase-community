from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.core.dependencies import get_project
from app.models.user import User
from app.schemas.projects import Project
from schemas.forgot_password import ForgotPasswordRequest, ResetPasswordRequest
from services.auth_service import AuthService
from services.email_service import EmailService
from models import AppUser
from core.database import get_db
import os

# Setup Jinja2 templates
template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
templates = Jinja2Templates(directory=template_dir)

router = APIRouter(prefix="/auth-collections", tags=["Reset-Password"])


@router.get("/reset-password-page", response_class=HTMLResponse)
async def reset_password_page(
    request: Request,
    token: str,
    db: Session = Depends(get_db),
):
    """
    Serve the password reset page.
    This is the default Cocobase-hosted reset password page.
    """
    # Verify token exists and get associated user to determine project
    reset_token = AuthService.verify_reset_token(db, token)

    if not reset_token:
        # Show error page for invalid token
        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "app_name": "Cocobase",
                "api_key": "",
                "login_url": None,
                "token": token,
            }
        )

    # Get user and project details
    user = db.query(AppUser).filter(AppUser.id == reset_token.user_id).first()
    if user:
        project = db.query(Project).filter(Project.id == user.client_id).first()
        if project:
            app_name = project.name if hasattr(project, 'name') else "Cocobase"
            api_key = project.api_key
            login_url = project.configs.get('LOGIN_URL') if project.configs else None

            return templates.TemplateResponse(
                "reset_password.html",
                {
                    "request": request,
                    "app_name": app_name,
                    "api_key": api_key,
                    "login_url": login_url,
                    "token": token,
                }
            )

    # Fallback
    return templates.TemplateResponse(
        "reset_password.html",
        {
            "request": request,
            "app_name": "Cocobase",
            "api_key": "",
            "login_url": None,
            "token": token,
        }
    )


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
    project = proj[0]
    email_service = EmailService(project_id=project.id, db=db)

    user = db.query(AppUser).filter(AppUser.email == request.email).first()

    if user:
        token = AuthService.create_reset_token(db, user.id)

        # Get password reset URL from project config or use Cocobase default
        reset_url = project.configs.get('PASSWORD_RESET_URL') if project.configs else None
        if not reset_url:
            # Default to Cocobase-hosted reset page
            reset_url = f"https://api.cocobase.buzz/auth-collections/reset-password-page"

        # Send password reset email using template
        await email_service.send_password_reset_email(
            to_email=user.email,
            token=token,
            reset_url_base=reset_url,
            app_name=project.name if hasattr(project, 'name') else "Cocobase"
        )
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

    # Send password changed confirmation email
    try:
        project = db.query(Project).filter(Project.id == user.client_id).first()
        if project:
            email_service = EmailService(project_id=project.id, db=db)
            await email_service.send_password_changed_email(
                to_email=user.email,
                app_name=project.name if hasattr(project, 'name') else "Cocobase"
            )
    except Exception as e:
        # Log the error but don't fail the password reset
        print(f"Failed to send password changed email: {e}")

    return {"message": "Password successfully reset"}
