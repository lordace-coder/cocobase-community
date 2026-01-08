from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.email_models import SMTPConfiguration
from app.models.integrations import Integration, ProjectIntegration
from app.services.integrations import IntegrationService


class EmailService:
    """Service class for sending of emails within a project"""

    def __init__(self, project_id: str, db: Session):
        self.project_id = project_id
        self.db = db

    def get_active_provider(self) -> ProjectIntegration | SMTPConfiguration:
        # Check for email integrations first (highest priority)
        db = self.db
        project_id = self.project_id

        email_integrations: ProjectIntegration = (
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
            return email_integrations

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
            return smtp_config
        raise Exception("No active email provider found for the project.")

    async def send_email(
        self,
        recipients: list[EmailStr],
        subject: str,
        body: str = None,
        template: str = None,
        template_data: dict = None,
    ):
        provider = self.get_active_provider()

        if isinstance(provider, ProjectIntegration):
            # Handle sending email via the selected integration
            integration_name = provider.integration.name

            service = IntegrationService(self.db)

            if integration_name == "cocomailer":
                return service.execute_integration(
                    self.project_id,
                    provider.integration_id,
                    function_name="send_mail",
                    config=provider.config,
                    to=recipients,
                    subject=subject,
                    body=body,
                    context=template_data,
                    template_id=template,
                )
            elif integration_name == "resend":
                return service.execute_integration(
                    self.project_id,
                    provider.integration_id,
                    function_name="send_email_resend",
                    config=provider.config,
                    to=recipients,
                    subject=subject,
                    html=body,
                )

            elif integration_name == "emailjs":
                raise NotImplementedError("EmailJS integration is not implemented yet.")
            else:
                raise Exception("Unsupported email integration.")

        elif isinstance(provider, SMTPConfiguration):
            # Handle sending email via SMTP
            conf = ConnectionConfig(
                MAIL_USERNAME=provider.username,
                MAIL_PASSWORD=provider.password,
                MAIL_FROM=provider.from_address,
                MAIL_PORT=provider.port,
                MAIL_SERVER=provider.server,
                MAIL_TLS=provider.use_tls,
                MAIL_SSL=provider.use_ssl,
                USE_CREDENTIALS=True,
            )

            message = MessageSchema(
                subject="Test Email",
                recipients=recipients,
                body=body,
                subtype="html",
            )
            fm = FastMail(conf)
            return await fm.send_message(message)


    async def send_password_reset_email(self, to_email: EmailStr, token: str):
        reset_link = f"https://api.cocobase.buzz/app/reset-password?token={token}"
        subject = "Password Reset Request"
        body = f"Click the link to reset your password: {reset_link}"

        await self.send_email(
            recipients=[to_email],
            subject=subject,
            body=body,
        )