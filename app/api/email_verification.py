from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel
import secrets

from app.core.database import get_db
from app.core.dependencies import get_project, get_app_user
from app.models.app_client import AppUser, Project, EmailVerificationToken
from app.models.user import User
from app.services.email_service import EmailService
from app.models.email_models import EmailTemplateTypeEnum

router = APIRouter(prefix="/auth-collections/verify-email", tags=["Email Verification"])

# Standalone verification router (no project dependency for frontend fallback)
standalone_router = APIRouter(tags=["Email Verification"])


class SendVerificationEmailRequest(BaseModel):
    """Request to send verification email"""
    pass


class VerifyEmailRequest(BaseModel):
    """Request to verify email with token"""
    token: str


def generate_verification_token() -> str:
    """Generate a secure verification token"""
    return secrets.token_urlsafe(32)


@router.post("/send")
async def send_verification_email(
    request: SendVerificationEmailRequest,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    proj_user: AppUser = Depends(get_app_user),
    proj: tuple[Project, User] = Depends(get_project),
):
    """
    Send email verification link to authenticated user.
    User must be authenticated to request verification email.
    """
    if not proj_user:
        raise HTTPException(401, "Authentication required")

    project = proj[0]

    # Check if email is already verified
    if proj_user.email_verified:
        return {"message": "Email already verified"}

    # Check for existing unused token created in the last 5 minutes
    existing_token = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.user_id == proj_user.id,
        EmailVerificationToken.client_id == project.id,
        EmailVerificationToken.is_used == False,
        EmailVerificationToken.created_at >= datetime.utcnow() - timedelta(minutes=5)
    ).first()

    if existing_token:
        # Token already sent recently, don't send another
        return {
            "message": "Verification email already sent. Please check your inbox or wait a few minutes before requesting again."
        }

    # Generate new token
    token = generate_verification_token()
    expiry_hours = 24  # Token valid for 24 hours

    verification_token = EmailVerificationToken(
        user_id=proj_user.id,
        client_id=project.id,
        token=token,
        expires_at=datetime.utcnow() + timedelta(hours=expiry_hours)
    )
    db.add(verification_token)
    db.commit()

    # Send email in background
    email_service = EmailService(project_id=project.id, db=db)
    user_name = getattr(proj_user, 'name', None) or getattr(proj_user, 'username', None) or proj_user.data.get('name') or proj_user.email.split('@')[0]

    # Get verification URL from project config or use default
    verification_base_url = None
    if project.configs:
        verification_base_url = project.configs.get('VERIFICATION_URL') or project.configs.get('FRONTEND_URL')

    if not verification_base_url:
        # Fallback to a default URL structure
        verification_base_url = f"https://api.cocobase.buzz/verify-email"

    verification_url = f"{verification_base_url}?token={token}"

    bg.add_task(
        send_verification_email_task,
        email_service=email_service,
        to_email=proj_user.email,
        user_name=user_name,
        app_name=project.name,
        verification_url=verification_url,
        expiry_hours=expiry_hours
    )

    return {
        "message": "Verification email sent successfully. Please check your inbox.",
        "expires_in_hours": expiry_hours
    }


@router.post("/verify")
async def verify_email(
    request: VerifyEmailRequest,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
):
    """
    Verify email address using token from verification link.
    This endpoint does not require authentication (user clicks link in email).
    """
    project = proj[0]

    # Find the token
    verification_token = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == request.token,
        EmailVerificationToken.client_id == project.id,
        EmailVerificationToken.is_used == False
    ).first()

    if not verification_token:
        raise HTTPException(400, "Invalid or expired verification token")

    # Check if token has expired
    if verification_token.expires_at < datetime.utcnow():
        raise HTTPException(400, "Verification token has expired. Please request a new one.")

    # Get the user
    user = db.query(AppUser).filter(
        AppUser.id == verification_token.user_id,
        AppUser.client_id == project.id
    ).first()

    if not user:
        raise HTTPException(404, "User not found")

    # Check if already verified
    if user.email_verified:
        return {
            "message": "Email already verified",
            "email_verified": True
        }

    # Mark email as verified
    user.email_verified = True
    user.email_verified_at = datetime.utcnow()

    # Mark token as used
    verification_token.is_used = True

    db.commit()

    return {
        "message": "Email verified successfully!",
        "email_verified": True,
        "verified_at": user.email_verified_at
    }


@router.post("/resend")
async def resend_verification_email(
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    proj_user: AppUser = Depends(get_app_user),
    proj: tuple[Project, User] = Depends(get_project),
):
    """
    Resend verification email to authenticated user.
    Alias for /send endpoint for clarity.
    """
    return await send_verification_email(
        request=SendVerificationEmailRequest(),
        bg=bg,
        db=db,
        proj_user=proj_user,
        proj=proj
    )


async def send_verification_email_task(
    email_service: EmailService,
    to_email: str,
    user_name: str,
    app_name: str,
    verification_url: str,
    expiry_hours: int
):
    """Background task to send verification email"""
    try:
        # Get template
        template = email_service.get_template(EmailTemplateTypeEnum.VERIFICATION)

        # Prepare context
        context = {
            'user_name': user_name,
            'app_name': app_name,
            'verification_url': verification_url,
            'expiry_hours': expiry_hours
        }

        # Render template
        html_body = email_service.render_template(template.body, context)
        subject = email_service.render_template(template.subject, context)

        # Send email
        await email_service.send_email(
            recipients=[to_email],
            subject=subject,
            body=html_body
        )

    except Exception as e:
        # Log error but don't fail the request
        print(f"Error sending verification email: {str(e)}")


def generate_verification_html(success: bool, message: str, project_name: str = "CocoBase") -> str:
    """Generate HTML response for email verification page"""
    status_color = "#10b981" if success else "#ef4444"
    status_icon = "✓" if success else "✕"
    status_text = "Verified!" if success else "Verification Failed"

    return f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Email Verification - {project_name}</title>
        <style>
            * {{
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 20px;
            }}
            .card {{
                background: white;
                border-radius: 16px;
                padding: 48px;
                max-width: 420px;
                width: 100%;
                text-align: center;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
            }}
            .icon {{
                width: 80px;
                height: 80px;
                border-radius: 50%;
                background: {status_color};
                display: flex;
                align-items: center;
                justify-content: center;
                margin: 0 auto 24px;
                font-size: 40px;
                color: white;
            }}
            h1 {{
                color: #1f2937;
                font-size: 24px;
                margin-bottom: 12px;
            }}
            .message {{
                color: #6b7280;
                font-size: 16px;
                line-height: 1.6;
                margin-bottom: 32px;
            }}
            .app-name {{
                color: #9ca3af;
                font-size: 14px;
                margin-top: 24px;
            }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="icon">{status_icon}</div>
            <h1>{status_text}</h1>
            <p class="message">{message}</p>
            <p class="app-name">Powered by {project_name}</p>
        </div>
    </body>
    </html>
    """


@standalone_router.get("/verify-email")
async def verify_email_frontend(
    token: str = Query(..., description="Verification token from email"),
    db: Session = Depends(get_db),
):
    """
    Frontend route for email verification.
    This handles verification when users click the link in their email
    and their project doesn't have a custom VERIFICATION_URL configured.
    """
    # Find the token (no project filter since this is a standalone route)
    verification_token = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == token,
        EmailVerificationToken.is_used == False
    ).first()

    if not verification_token:
        return HTMLResponse(
            content=generate_verification_html(
                success=False,
                message="This verification link is invalid or has already been used. Please request a new verification email."
            ),
            status_code=400
        )

    # Check if token has expired
    if verification_token.expires_at < datetime.utcnow():
        return HTMLResponse(
            content=generate_verification_html(
                success=False,
                message="This verification link has expired. Please request a new verification email."
            ),
            status_code=400
        )

    # Get the user
    user = db.query(AppUser).filter(
        AppUser.id == verification_token.user_id,
        AppUser.client_id == verification_token.client_id
    ).first()

    if not user:
        return HTMLResponse(
            content=generate_verification_html(
                success=False,
                message="User account not found. Please contact support."
            ),
            status_code=404
        )

    # Get project name for branding
    project = db.query(Project).filter(Project.id == verification_token.client_id).first()
    project_name = project.name if project else "CocoBase"

    # Check if already verified
    if user.email_verified:
        return HTMLResponse(
            content=generate_verification_html(
                success=True,
                message="Your email address has already been verified. You can close this page.",
                project_name=project_name
            )
        )

    # Mark email as verified
    user.email_verified = True
    user.email_verified_at = datetime.utcnow()

    # Mark token as used
    verification_token.is_used = True

    db.commit()

    # Check if project has a redirect URL configured
    redirect_url = None
    if project and project.configs:
        redirect_url = project.configs.get('VERIFICATION_SUCCESS_URL')
        
    if redirect_url:
        # Redirect to project's frontend with success status
        separator = "&" if "?" in redirect_url else "?"
        return RedirectResponse(url=f"{redirect_url}{separator}email_verified=true")

    return HTMLResponse(
        content=generate_verification_html(
            success=True,
            message="Your email address has been successfully verified! You can now close this page and continue using the app.",
            project_name=project_name
        )
    )
