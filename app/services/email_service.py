from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from pydantic import EmailStr
from sqlalchemy import and_
from sqlalchemy.orm import Session
from datetime import datetime
import os

from app.models.email_models import SMTPConfiguration, DefaultEmailTemplate, ProjectEmailTemplate, EmailTemplateTypeEnum, EmailLog, EmailStatusEnum
from app.models.integrations import Integration, ProjectIntegration
from app.services.integrations import IntegrationService


class EmailService:
    """Service class for sending of emails within a project"""

    def __init__(self, project_id: str, db: Session):
        self.project_id = project_id
        self.db = db

    def get_template(self, template_type: EmailTemplateTypeEnum):
        """
        Get email template for the project.
        First checks for project-specific template, then falls back to default template.
        """
        # Try to get project-specific template first
        project_template = (
            self.db.query(ProjectEmailTemplate)
            .filter(
                and_(
                    ProjectEmailTemplate.project_id == self.project_id,
                    ProjectEmailTemplate.template_type == template_type,
                    ProjectEmailTemplate.is_active == True,
                )
            )
            .first()
        )

        if project_template:
            return project_template

        # Fall back to default template
        default_template = (
            self.db.query(DefaultEmailTemplate)
            .filter(
                and_(
                    DefaultEmailTemplate.template_type == template_type,
                    DefaultEmailTemplate.is_active == True,
                )
            )
            .first()
        )

        if not default_template:
            raise Exception(f"No template found for type: {template_type.value}")

        return default_template

    def render_template(self, template_body: str, context: dict) -> str:
        """
        Simple template rendering using string replacement.
        Replaces {{variable}} with values from context dict.
        """
        rendered = template_body
        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            rendered = rendered.replace(placeholder, str(value))
        return rendered

    def get_active_provider(self) -> ProjectIntegration | SMTPConfiguration | dict:
        """
        Get active email provider for the project.
        Priority: Project Integration > SMTP Config > Cocobase Fallback
        """
        db = self.db
        project_id = self.project_id

        # Priority 1: Check for email integrations
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

        # Priority 2: Fallback to SMTP config
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

        # Priority 3: Use Cocobase fallback (Resend)
        # This allows users to test forgot password without setting up email
        cocobase_resend_key = os.getenv('COCOBASE_RESEND_API_KEY')
        if cocobase_resend_key:
            return {
                'type': 'cocobase_fallback',
                'provider': 'resend',
                'api_key': cocobase_resend_key,
                'from_email': 'noreply@cocobase.buzz',
                'from_name': 'Cocobase'
            }

        raise Exception("No active email provider found for the project and no Cocobase fallback configured.")

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
                return service.execute_integration(
                    self.project_id,
                    provider.integration_id,
                    function_name="send_email",
                    config=provider.config,
                    to_email=recipients,
                    subject=subject,
                    html=body,
                ) 
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
                subject=subject,
                recipients=recipients,
                body=body,
                subtype="html",
            )
            fm = FastMail(conf)
            return await fm.send_message(message)

        elif isinstance(provider, dict) and provider.get('type') == 'cocobase_fallback':
            # Handle Cocobase fallback using Resend
            import httpx

            resend_api_key = provider['api_key']
            from_email = provider['from_email']
            from_name = provider['from_name']

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    'https://api.resend.com/emails',
                    headers={
                        'Authorization': f'Bearer {resend_api_key}',
                        'Content-Type': 'application/json',
                    },
                    json={
                        'from': f'{from_name} <{from_email}>',
                        'to': recipients,
                        'subject': subject,
                        'html': body,
                    }
                )

                if response.status_code != 200:
                    raise Exception(f"Cocobase fallback email failed: {response.text}")

                return response.json()


    async def send_password_reset_email(
        self,
        to_email: EmailStr,
        token: str,
        reset_url_base: str = "https://app.cocobase.buzz/reset-password",
        app_name: str = "Cocobase",
        expiry_hours: int = 24
    ):
        """
        Send password reset email using template.

        Args:
            to_email: Recipient email address
            token: Password reset token
            reset_url_base: Base URL for password reset (token will be appended)
            app_name: Name of the application
            expiry_hours: Number of hours until token expires
        """
        try:
            # Get the template
            template = self.get_template(EmailTemplateTypeEnum.FORGOT_PASSWORD)

            # Prepare template context
            reset_link = f"{reset_url_base}?token={token}"
            context = {
                "reset_link": reset_link,
                "app_name": app_name,
                "expiry_hours": expiry_hours,
                "year": datetime.now().year
            }

            # Render templates
            subject = self.render_template(template.subject, context)
            html_body = self.render_template(template.html_body, context)
            text_body = self.render_template(template.text_body, context)

            # Log the email
            email_log = EmailLog(
                project_id=self.project_id,
                recipients=[to_email],
                subject=subject,
                template_type=EmailTemplateTypeEnum.FORGOT_PASSWORD,
                used_default_template=isinstance(template, DefaultEmailTemplate),
                template_id=str(template.id),
                status=EmailStatusEnum.PENDING
            )
            self.db.add(email_log)
            self.db.commit()

            # Send the email
            await self.send_email(
                recipients=[to_email],
                subject=subject,
                body=html_body,
            )

            # Update log status
            email_log.status = EmailStatusEnum.SENT
            email_log.sent_at = datetime.now()
            self.db.commit()

        except Exception as e:
            # Update log with error if log was created
            if 'email_log' in locals():
                email_log.status = EmailStatusEnum.FAILED
                email_log.error_message = str(e)
                self.db.commit()
            raise

    async def send_password_changed_email(
        self,
        to_email: EmailStr,
        app_name: str = "Cocobase"
    ):
        """
        Send password changed confirmation email using template.

        Args:
            to_email: Recipient email address
            app_name: Name of the application
        """
        try:
            # Get the template
            template = self.get_template(EmailTemplateTypeEnum.PASSWORD_CHANGED)

            # Prepare template context
            now = datetime.now()
            context = {
                "app_name": app_name,
                "change_date": now.strftime("%B %d, %Y"),
                "change_time": now.strftime("%I:%M %p"),
                "year": now.year
            }

            # Render templates
            subject = self.render_template(template.subject, context)
            html_body = self.render_template(template.html_body, context)
            text_body = self.render_template(template.text_body, context)

            # Log the email
            email_log = EmailLog(
                project_id=self.project_id,
                recipients=[to_email],
                subject=subject,
                template_type=EmailTemplateTypeEnum.PASSWORD_CHANGED,
                used_default_template=isinstance(template, DefaultEmailTemplate),
                template_id=str(template.id),
                status=EmailStatusEnum.PENDING
            )
            self.db.add(email_log)
            self.db.commit()

            # Send the email
            await self.send_email(
                recipients=[to_email],
                subject=subject,
                body=html_body,
            )

            # Update log status
            email_log.status = EmailStatusEnum.SENT
            email_log.sent_at = datetime.now()
            self.db.commit()

        except Exception as e:
            # Update log with error if log was created
            if 'email_log' in locals():
                email_log.status = EmailStatusEnum.FAILED
                email_log.error_message = str(e)
                self.db.commit()
            raise
    async def send_welcome_email(
        self,
        to_email: EmailStr,
        user_name: str = None,
        app_name: str = "Cocobase",
        login_url: str = None
    ):
        """
        Send welcome email to new user using template.

        Args:
            to_email: Recipient email address
            user_name: User's name (defaults to email if not provided)
            app_name: Name of the application
            login_url: URL to login page
        """
        try:
            # Get the template
            template = self.get_template(EmailTemplateTypeEnum.WELCOME)

            # Prepare template context
            now = datetime.now()
            context = {
                "app_name": app_name,
                "user_name": user_name or to_email.split('@')[0],
                "user_email": to_email,
                "join_date": now.strftime("%B %d, %Y"),
                "login_url": login_url or "https://app.cocobase.buzz/login",
                "year": now.year
            }

            # Render templates
            subject = self.render_template(template.subject, context)
            html_body = self.render_template(template.html_body, context)
            text_body = self.render_template(template.text_body, context)

            # Log the email
            email_log = EmailLog(
                project_id=self.project_id,
                recipients=[to_email],
                subject=subject,
                template_type=EmailTemplateTypeEnum.WELCOME,
                used_default_template=isinstance(template, DefaultEmailTemplate),
                template_id=str(template.id),
                status=EmailStatusEnum.PENDING
            )
            self.db.add(email_log)
            self.db.commit()

            # Send the email
            await self.send_email(
                recipients=[to_email],
                subject=subject,
                body=html_body,
            )

            # Update log status
            email_log.status = EmailStatusEnum.SENT
            email_log.sent_at = datetime.now()
            self.db.commit()

        except Exception as e:
            # Update log with error if log was created
            if 'email_log' in locals():
                email_log.status = EmailStatusEnum.FAILED
                email_log.error_message = str(e)
                self.db.commit()
            # Don't raise - welcome email failure shouldn't block signup
            print(f"Failed to send welcome email: {e}")

    async def send_2fa_code_email(
        self,
        to_email: EmailStr,
        code: str,
        user_name: str = None,
        app_name: str = "Cocobase",
        expiry_minutes: int = 10
    ):
        """
        Send 2FA verification code email using template.

        Args:
            to_email: Recipient email address
            code: 6-digit verification code
            user_name: User's name (defaults to email if not provided)
            app_name: Name of the application
            expiry_minutes: Minutes until code expires
        """
        try:
            # Get the template
            template = self.get_template(EmailTemplateTypeEnum.LOGIN_ALERT)

            # Prepare template context
            now = datetime.now()
            context = {
                "app_name": app_name,
                "user_name": user_name or to_email.split('@')[0],
                "code": code,
                "expiry_minutes": expiry_minutes,
                "year": now.year
            }

            # Render templates
            subject = self.render_template(template.subject, context)
            html_body = self.render_template(template.html_body, context)
            text_body = self.render_template(template.text_body, context)

            # Log the email
            email_log = EmailLog(
                project_id=self.project_id,
                recipients=[to_email],
                subject=subject,
                template_type=EmailTemplateTypeEnum.LOGIN_ALERT,
                used_default_template=isinstance(template, DefaultEmailTemplate),
                template_id=str(template.id),
                status=EmailStatusEnum.PENDING
            )
            self.db.add(email_log)
            self.db.commit()

            # Send the email
            await self.send_email(
                recipients=[to_email],
                subject=subject,
                body=html_body,
            )

            # Update log status
            email_log.status = EmailStatusEnum.SENT
            email_log.sent_at = datetime.now()
            self.db.commit()

        except Exception as e:
            # Update log with error if log was created
            if 'email_log' in locals():
                email_log.status = EmailStatusEnum.FAILED
                email_log.error_message = str(e)
                self.db.commit()
            raise  # 2FA email failure should be raised
