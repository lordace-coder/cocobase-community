from sqladmin import BaseView, expose
from starlette.requests import Request
from starlette.responses import RedirectResponse
from sqlalchemy import select
from app.models.user import User
from app.services.email import send_message_email
from app.core.database import SessionLocal


class EmailSenderView(BaseView):
    name = "Email Users"
    icon = "fa-solid fa-envelope"

    @expose("/email-users", methods=["GET", "POST"])
    async def send_email_view(self, request: Request):
        """View for sending emails to users"""
        session = SessionLocal()

        # Handle form submission
        if request.method == "POST":
            form_data = await request.form()

            # Get form data
            recipient_type = form_data.get("recipient_type")
            selected_user_ids = form_data.getlist("selected_users")
            subject = form_data.get("subject")
            message = form_data.get("message")

            # Validate inputs
            if not subject or not message:
                error = "Subject and message are required"
                users = session.execute(select(User)).scalars().all()
                return await self.templates.TemplateResponse(
                    request,
                    "sqladmin/email_sender.html",
                    {
                        "users": users,
                        "error": error,
                    },
                )

            # Determine recipients
            recipients = []
            if recipient_type == "all":
                recipients = session.execute(select(User)).scalars().all()
            elif recipient_type == "selected":
                if not selected_user_ids:
                    error = "Please select at least one user"
                    users = session.execute(select(User)).scalars().all()
                    return await self.templates.TemplateResponse(
                        request,
                        "sqladmin/email_sender.html",
                        {
                            "users": users,
                            "error": error,
                        },
                    )
                recipients = session.execute(
                    select(User).where(User.id.in_(selected_user_ids))
                ).scalars().all()

            # Send emails
            success_count = 0
            fail_count = 0

            for user in recipients:
                try:
                    await send_message_email(
                        to_email=user.email,
                        user_name=user.username or user.full_name or "User",
                        message=message,
                        title=subject,
                    )
                    success_count += 1
                except Exception as e:
                    print(f"Failed to send email to {user.email}: {e}")
                    fail_count += 1

            session.close()

            # Return success page with results
            return await self.templates.TemplateResponse(
                request,
                "sqladmin/email_sender_success.html",
                {
                    "success_count": success_count,
                    "fail_count": fail_count,
                    "total": success_count + fail_count,
                },
            )

        # GET request - show form
        users = session.execute(select(User)).scalars().all()
        session.close()

        return await self.templates.TemplateResponse(
            request,
            "sqladmin/email_sender.html",
            {
                "users": users,
                "error": None,
            },
        )
