import httpx
import os
from dotenv import load_dotenv

from app.models.app_client import Project
from app.models.user import User

load_dotenv()
key = os.getenv("MAILER_API_KEY")
if not key:
    raise ValueError("MAILER_API_KEY is not set in the environment variables.")


async def send_email(
    to: str | list, subject: str, template: str, context: dict = None
) -> bool:
    """
    Send email asynchronously using httpx

    Args:
        to: Email address(es) - string or list
        subject: Email subject line
        template: Template key/identifier
        context: Dictionary of template variables (default: {"name": "John Doe"})

    Returns:
        bool: True if successful, False otherwise
    """
    if isinstance(to, str):
        to = [to]
    else:
        to = list(set(to))

    if context is None:
        context = {"name": "John Doe"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"https://coco-mailer-api.vercel.app/api/send-mail/{key}?template_key={template}",
                json={
                    "recipient_list": to,
                    "subject": subject,
                    "is_html": True,
                    "context": context,
                },
            )
            print(response.json(), "reponse")
            response.raise_for_status()
            return True
    except httpx.HTTPError as e:
        print(f"Error sending email: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False


async def send_subscription_email(
    to_email,
    user_name,
    plan_name,
    amount,
    currency,
    subscription_end_date,
):
    await send_email(
        to=to_email,
        subject="Successfull Subscription",
        context={
            "user_name": user_name,
            "plan_name": plan_name,
            "amount": amount,
            "currency": currency,
            "subscription_end_date": subscription_end_date,
        },
        template="98628178-1446-427f-88f5-aa4ac29ecce2",
    )


async def send_message_email(
    to_email,
    user_name,
    message,
    title,
):
    await send_email(
        to=to_email,
        subject=title,
        context={
            "user_name": user_name,
            "message": message,
            "title": title,
        },
        template="1fe572fb-269c-4ac4-84fd-db3b274883a7",
    )


# Notification function stubs (implement your logic)
def notify_limit_reached(user: User, project: Project, resource_type: str, limit: int):
    """
    Send notification when resource limit is reached and project is deactivated.

    Args:
        user: The project owner
        project: The affected project
        resource_type: Type of resource (users, storage, requests, etc.)
        limit: The limit that was reached
    """
    # Your notification logic here
    # Examples:
    # - Send email
    # - Send SMS
    # - Create in-app notification
    # - Send webhook
    # - Log to monitoring system
    pass


def notify_limit_warning(user, project, resource_type, current_usage, limit, severity):
    percentage = (current_usage / limit) * 100

    if severity == "critical":
        subject = (
            f"⚠️ URGENT: {project.name} at {percentage:.0f}% {resource_type} capacity"
        )
        message = f"You're using {current_usage} of {limit} {resource_type}. Add more soon or your project will be deactivated!"
    else:
        subject = f"📊 {project.name} at {percentage:.0f}% {resource_type} capacity"
        message = f"You're using {current_usage} of {limit} {resource_type}. Consider upgrading your plan."

    # Send email, SMS, push notification, etc.
