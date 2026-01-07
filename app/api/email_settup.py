from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import List, Optional, Annotated
from pydantic import BaseModel, EmailStr
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.dependencies import get_current_user, verify_project_access
from app.models.app_client import Project
from app.models.user import User
from app.schemas.email_settup_schemas import *
from app.core.database import get_db
from app.models.email_models import (
    SMTPConfiguration,
    DefaultEmailTemplate,
    ProjectEmailTemplate,
    EmailLog,
    EmailTemplateTypeEnum,
    EmailStatusEnum,
)
from app.models.integrations import Integration, ProjectIntegration

# Router-level dependency for authentication
router = APIRouter(
    prefix="/project-mailer/{project_id}",
    tags=["email"],
    dependencies=[Depends(get_current_user)],
)


# Reusable dependency for project access verification
async def verify_project_access_dep(
    project_id: Annotated[str, Path()],
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Dependency to verify user has access to the project"""
    verify_project_access(user, project_id, db)
    return user


# ============= SMTP Configuration Routes =============


@router.post(
    "/smtp", response_model=SMTPConfigResponse, status_code=status.HTTP_201_CREATED
)
def create_smtp_config(
    config: SMTPConfigCreate,
    user: Annotated[User, Depends(verify_project_access_dep)],
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str, Path()],
):
    """Create SMTP configuration for a project"""
    # Check if SMTP config already exists
    existing = (
        db.query(SMTPConfiguration)
        .filter(SMTPConfiguration.project_id == project_id)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SMTP configuration already exists for this project",
        )

    smtp_config = SMTPConfiguration(project_id=project_id, **config.model_dump())

    db.add(smtp_config)
    db.commit()
    db.refresh(smtp_config)

    return smtp_config


@router.get("/smtp", response_model=SMTPConfigResponse)
def get_smtp_config(
    user: Annotated[User, Depends(verify_project_access_dep)],
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str, Path()],
):
    """Get SMTP configuration for a project"""
    smtp_config = (
        db.query(SMTPConfiguration)
        .filter(SMTPConfiguration.project_id == project_id)
        .first()
    )

    if not smtp_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="SMTP configuration not found"
        )

    return smtp_config


@router.patch("/smtp", response_model=SMTPConfigResponse)
def update_smtp_config(
    config: SMTPConfigUpdate,
    user: Annotated[User, Depends(verify_project_access_dep)],
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str, Path()],
):
    """Update SMTP configuration"""
    smtp_config = (
        db.query(SMTPConfiguration)
        .filter(SMTPConfiguration.project_id == project_id)
        .first()
    )

    if not smtp_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="SMTP configuration not found"
        )

    for key, value in config.model_dump(exclude_unset=True).items():
        setattr(smtp_config, key, value)

    db.commit()
    db.refresh(smtp_config)

    return smtp_config


@router.delete("/smtp", status_code=status.HTTP_204_NO_CONTENT)
def delete_smtp_config(
    user: Annotated[User, Depends(verify_project_access_dep)],
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str, Path()],
):
    """Delete SMTP configuration"""
    smtp_config = (
        db.query(SMTPConfiguration)
        .filter(SMTPConfiguration.project_id == project_id)
        .first()
    )

    if not smtp_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="SMTP configuration not found"
        )

    db.delete(smtp_config)
    db.commit()


@router.post("/smtp/test")
def test_smtp_connection(
    user: Annotated[User, Depends(verify_project_access_dep)],
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str, Path()],
):
    """Test SMTP connection"""
    smtp_config = (
        db.query(SMTPConfiguration)
        .filter(SMTPConfiguration.project_id == project_id)
        .first()
    )

    if not smtp_config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="SMTP configuration not found"
        )

    try:
        if smtp_config.use_ssl:
            server = smtplib.SMTP_SSL(smtp_config.host, smtp_config.port, timeout=10)
        else:
            server = smtplib.SMTP(smtp_config.host, smtp_config.port, timeout=10)
            if smtp_config.use_tls:
                server.starttls()

        server.login(smtp_config.username, smtp_config.password)
        server.quit()

        # Update verification status
        smtp_config.is_verified = True
        smtp_config.last_verified_at = datetime.utcnow()
        db.commit()

        return {"success": True, "message": "SMTP connection successful"}

    except Exception as e:
        smtp_config.is_verified = False
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SMTP connection failed: {str(e)}",
        )


# ============= Email Provider Routes =============


@router.get("/provider", response_model=EmailProviderResponse)
def get_active_email_provider(
    user: Annotated[User, Depends(verify_project_access_dep)],
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str, Path()],
):
    """Get the active email provider for a project (SMTP or integration)"""
    # Priority: Integrations (Cocomailer, Resend, EmailJS) > SMTP

    # Check for email integrations first (highest priority)
    email_integrations = (
        db.query(ProjectIntegration)
        .join(Integration)
        .filter(
            and_(
                ProjectIntegration.project_id == project_id,
                ProjectIntegration.is_enabled == True,
                Integration.name.in_(["cocomailer", "resend", "emailjs"]),
            )
        )
        .first()
    )

    if email_integrations:
        return EmailProviderResponse(
            provider_type=email_integrations.integration.name,
            config=email_integrations.config,
            is_active=True,
        )

    # Fallback to SMTP config (lowest priority)
    smtp_config = (
        db.query(SMTPConfiguration)
        .filter(
            and_(
                SMTPConfiguration.project_id == project_id,
                SMTPConfiguration.is_active == True,
            )
        )
        .first()
    )

    if smtp_config:
        return EmailProviderResponse(
            provider_type="smtp",
            config={
                "host": smtp_config.host,
                "port": smtp_config.port,
                "from_email": smtp_config.from_email,
                "is_verified": smtp_config.is_verified,
            },
            is_active=True,
        )

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="No active email provider configured",
    )


# ============= Template Routes =============


@router.get("/templates/system", response_model=List[TemplateResponse])
def get_system_templates(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Get all system default templates"""
    templates = (
        db.query(DefaultEmailTemplate)
        .filter(DefaultEmailTemplate.is_active == True)
        .all()
    )

    return templates


@router.get("/templates/system/{template_type}", response_model=TemplateResponse)
def get_system_template(
    template_type: EmailTemplateTypeEnum,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
):
    """Get a specific system template"""
    template = (
        db.query(DefaultEmailTemplate)
        .filter(
            and_(
                DefaultEmailTemplate.template_type == template_type,
                DefaultEmailTemplate.is_active == True,
            )
        )
        .first()
    )

    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"System template '{template_type}' not found",
        )

    return template


@router.get("/templates", response_model=List[ProjectTemplateResponse])
def get_project_templates(
    user: Annotated[User, Depends(verify_project_access_dep)],
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str, Path()],
):
    """Get all templates for a project (including overrides)"""
    templates = (
        db.query(ProjectEmailTemplate)
        .filter(
            and_(
                ProjectEmailTemplate.project_id == project_id,
                ProjectEmailTemplate.is_active == True,
            )
        )
        .all()
    )

    return templates


@router.post(
    "/templates",
    response_model=ProjectTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_project_template(
    template: TemplateCreate,
    user: Annotated[User, Depends(verify_project_access_dep)],
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str, Path()],
):
    """Create or override a template for a project"""
    # Check if template already exists
    existing = (
        db.query(ProjectEmailTemplate)
        .filter(
            and_(
                ProjectEmailTemplate.project_id == project_id,
                ProjectEmailTemplate.template_type == template.template_type,
            )
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Template for '{template.template_type}' already exists",
        )

    # Check if overriding a default template
    default_template = (
        db.query(DefaultEmailTemplate)
        .filter(DefaultEmailTemplate.template_type == template.template_type)
        .first()
    )

    project_template = ProjectEmailTemplate(
        project_id=project_id,
        is_default_override=bool(default_template),
        created_by=user.id,
        **template.model_dump(),
    )

    db.add(project_template)
    db.commit()
    db.refresh(project_template)

    return project_template


@router.patch("/templates/{template_id}", response_model=ProjectTemplateResponse)
def update_project_template(
    template_id: int,
    template: TemplateUpdate,
    user: Annotated[User, Depends(verify_project_access_dep)],
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str, Path()],
):
    """Update a project template"""
    project_template = (
        db.query(ProjectEmailTemplate)
        .filter(
            and_(
                ProjectEmailTemplate.id == template_id,
                ProjectEmailTemplate.project_id == project_id,
            )
        )
        .first()
    )

    if not project_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    for key, value in template.model_dump(exclude_unset=True).items():
        setattr(project_template, key, value)

    db.commit()
    db.refresh(project_template)

    return project_template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_template(
    template_id: int,
    user: Annotated[User, Depends(verify_project_access_dep)],
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str, Path()],
):
    """Delete a project template"""
    project_template = (
        db.query(ProjectEmailTemplate)
        .filter(
            and_(
                ProjectEmailTemplate.id == template_id,
                ProjectEmailTemplate.project_id == project_id,
            )
        )
        .first()
    )

    if not project_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Template not found"
        )

    db.delete(project_template)
    db.commit()


# ============= Email Sending Routes =============


def get_template_content(
    project_id: str, template_type: EmailTemplateTypeEnum, db: Session
):
    """Get template content (project template or default)"""
    # Check for project-specific template first
    project_template = (
        db.query(ProjectEmailTemplate)
        .filter(
            and_(
                ProjectEmailTemplate.project_id == project_id,
                ProjectEmailTemplate.template_type == template_type,
                ProjectEmailTemplate.is_active == True,
            )
        )
        .first()
    )

    if project_template:
        return project_template, False

    # Fallback to default template
    default_template = (
        db.query(DefaultEmailTemplate)
        .filter(
            and_(
                DefaultEmailTemplate.template_type == template_type,
                DefaultEmailTemplate.is_active == True,
            )
        )
        .first()
    )

    if not default_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No template found for '{template_type}'",
        )

    return default_template, True


def render_template(template_str: str, variables: dict) -> str:
    """Simple template variable replacement"""
    for key, value in variables.items():
        template_str = template_str.replace(f"{{{{{key}}}}}", str(value))
    return template_str


def send_via_smtp(
    smtp_config: SMTPConfiguration,
    recipients: List[str],
    subject: str,
    html_body: str,
    text_body: str,
):
    """Send email via SMTP"""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = (
        f"{smtp_config.from_name} <{smtp_config.from_email}>"
        if smtp_config.from_name
        else smtp_config.from_email
    )
    msg["To"] = ", ".join(recipients)

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    if smtp_config.use_ssl:
        server = smtplib.SMTP_SSL(smtp_config.host, smtp_config.port)
    else:
        server = smtplib.SMTP(smtp_config.host, smtp_config.port)
        if smtp_config.use_tls:
            server.starttls()

    server.login(smtp_config.username, smtp_config.password)
    server.send_message(msg)
    server.quit()


@router.post("/send", response_model=EmailLogResponse)
def send_email(
    request: SendEmailRequest,
    user: Annotated[User, Depends(verify_project_access_dep)],
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str, Path()],
):
    """Send an email using configured provider"""
    # Get template
    template, is_default = get_template_content(project_id, request.template_type, db)

    # Render template with variables
    subject = request.subject_override or render_template(
        template.subject, request.variables
    )
    html_body = render_template(template.html_body, request.variables)
    text_body = render_template(template.text_body, request.variables)

    # Create email log
    email_log = EmailLog(
        project_id=project_id,
        recipients=request.recipients,
        subject=subject,
        template_type=request.template_type,
        used_default_template=is_default,
        template_id=str(template.id),
        status=EmailStatusEnum.PENDING,
    )
    db.add(email_log)
    db.commit()

    try:
        # Get active email provider
        smtp_config = (
            db.query(SMTPConfiguration)
            .filter(
                and_(
                    SMTPConfiguration.project_id == project_id,
                    SMTPConfiguration.is_active == True,
                )
            )
            .first()
        )

        if smtp_config:
            # Send via SMTP
            send_via_smtp(
                smtp_config, request.recipients, subject, html_body, text_body
            )
        else:
            # Check for integrations
            # TODO: Implement integration-based sending (Cocomailer, Resend, etc.)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active email provider configured",
            )

        # Update log status
        email_log.status = EmailStatusEnum.SENT
        email_log.sent_at = datetime.utcnow()

    except Exception as e:
        email_log.status = EmailStatusEnum.FAILED
        email_log.error_message = str(e)

    db.commit()
    db.refresh(email_log)

    if email_log.status == EmailStatusEnum.FAILED:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send email: {email_log.error_message}",
        )

    return email_log


# ============= Email Logs Routes =============


@router.get("/logs", response_model=List[EmailLogResponse])
def get_email_logs(
    project_id: str ,

    status_filter: Optional[EmailStatusEnum] = None,
    limit: int = 50,
    offset: int = 0,
    user: Annotated[User, Depends(verify_project_access_dep)] = None,
    db: Annotated[Session, Depends(get_db)] = None,
):
    """Get email logs for a project"""
    query = db.query(EmailLog).filter(EmailLog.project_id == project_id)

    if status_filter:
        query = query.filter(EmailLog.status == status_filter)

    logs = query.order_by(EmailLog.created_at.desc()).limit(limit).offset(offset).all()

    return logs


@router.get("/logs/{log_id}", response_model=EmailLogResponse)
def get_email_log(
    log_id: int,
    user: Annotated[User, Depends(verify_project_access_dep)],
    db: Annotated[Session, Depends(get_db)],
    project_id: Annotated[str, Path()],
):
    """Get a specific email log"""
    log = (
        db.query(EmailLog)
        .filter(and_(EmailLog.id == log_id, EmailLog.project_id == project_id))
        .first()
    )

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email log not found"
        )

    return log
