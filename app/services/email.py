import os
from dotenv import load_dotenv
import resend
from app.models.app_client import Project
from app.models.user import User
from app.services.email_utils import get_email_template, get_email_verification_template, get_password_reset_template

load_dotenv()

# Configure Resend API key
resend.api_key = os.getenv("RESEND_API_KEY")
if not resend.api_key:
    raise ValueError("RESEND_API_KEY is not set in the environment variables.")

# Your verified sender email
FROM_EMAIL = "support@cocobase.buzz"


def send_email(
    to: str | list,
    subject: str,
    html_content: str,
    tags: list[dict] = None
) -> dict | None:
    """
    Send email using Resend SDK
    
    Args:
        to: Email address(es) - string or list
        subject: Email subject line
        html_content: HTML content of the email
        tags: Optional list of tag dicts like [{"name": "type", "value": "subscription"}]
        
    Returns:
        dict: Response from Resend API with id, or None if failed
    """
    if isinstance(to, str):
        to = [to]
    else:
        to = list(set(to))
    
    params = {
        "from": FROM_EMAIL,
        "to": to,
        "subject": subject,
        "html": html_content,
    }
    
    # Add tags if provided
    if tags:
        params["tags"] = tags
    
    try:
        response = resend.Emails.send(params)
        print(f"Email sent successfully. ID: {response.get('id')}")
        return response
            
    except Exception as e:
        print(f"Error sending email via Resend: {e}")
        return None


async def send_subscription_email(
    to_email: str,
    user_name: str,
    plan_name: str,
    amount: float,
    currency: str,
    subscription_end_date: str,
):
    """Send subscription confirmation email"""
    message = f"""Hello {user_name},

Thank you for subscribing to {plan_name}!

Subscription Details:
• Plan: {plan_name}
• Amount: {amount} {currency}
• Valid until: {subscription_end_date}

Your subscription is now active and you can enjoy all the premium features.

If you have any questions, feel free to reach out to our support team.

Best regards,
The Cocobase Team"""

    html_content = get_email_template("Successful Subscription", message)
    
    send_email(
        to=to_email,
        subject="Successful Subscription - Cocobase",
        html_content=html_content,
        tags=[
            {"name": "type", "value": "subscription"},
            {"name": "plan", "value": plan_name},
            {"name": "user", "value": user_name},
        ]
    )


async def send_message_email(
    to_email: str,
    user_name: str,
    message: str,
    title: str,
):
    """Send general message email"""
    formatted_message = f"Hello {user_name},\n\n{message}"
    html_content = get_email_template(title, formatted_message)
    
    send_email(
        to=to_email,
        subject=title,
        html_content=html_content,
        tags=[
            {"name": "type", "value": "message"},
            {"name": "user", "value": user_name},
        ]
    )


async def notify_limit_reached(
    user: User,
    project: Project,
    resource_type: str,
    limit: int
):
    """
    Send notification when resource limit is reached and project is deactivated.
    """
    message = f"""Hello {user.name},

Your project "{project.name}" has reached its {resource_type} limit of {limit}.

⚠️ Your project has been automatically deactivated to prevent overages.

To reactivate your project, please:
1. Upgrade your plan to get more {resource_type}
2. Or reduce your current usage

Visit your dashboard to take action: https://www.cocobase.buzz/dashboard

Best regards,
The Cocobase Team"""

    html_content = get_email_template(
        f"Project Deactivated - {resource_type.title()} Limit Reached",
        message
    )
    
    send_email(
        to=user.email,
        subject=f"🚨 Project Deactivated - {project.name}",
        html_content=html_content,
        tags=[
            {"name": "type", "value": "limit_reached"},
            {"name": "project_id", "value": str(project.id)},
            {"name": "resource_type", "value": resource_type},
        ]
    )


async def notify_limit_warning(
    user: User,
    project: Project,
    resource_type: str,
    current_usage: int,
    limit: int,
    severity: str
):
    """
    Send warning notification when approaching resource limits.
    """
    percentage = (current_usage / limit) * 100
    
    if severity == "critical":
        emoji = "⚠️"
        subject = f"⚠️ URGENT: {project.name} at {percentage:.0f}% {resource_type} capacity"
        urgency = "URGENT: "
        action_text = "Add more soon or your project will be deactivated!"
    else:
        emoji = "📊"
        subject = f"📊 {project.name} at {percentage:.0f}% {resource_type} capacity"
        urgency = ""
        action_text = "Consider upgrading your plan to avoid service interruption."
    
    message = f"""Hello {user.name},

{emoji} {urgency}Your project "{project.name}" is running low on {resource_type}.

Current Usage: {current_usage} of {limit} ({percentage:.1f}%)

{action_text}

View your usage and upgrade options: https://www.cocobase.buzz/dashboard/projects/{project.id}

Best regards,
The Cocobase Team"""

    html_content = get_email_template(
        f"{resource_type.title()} Usage Alert - {project.name}",
        message
    )
    
    send_email(
        to=user.email,
        subject=subject,
        html_content=html_content,
        tags=[
            {"name": "type", "value": "limit_warning"},
            {"name": "severity", "value": severity},
            {"name": "project_id", "value": str(project.id)},
            {"name": "resource_type", "value": resource_type},
        ]
    )


def send_password_reset_email(
    to_email: str,
    username: str,
    reset_link: str,
):
    """
    Send password reset email with secure reset link
    
    Args:
        to_email: User's email address
        username: User's display name
        reset_link: Password reset URL (should include token and expire in 1 hour)
    """
    html_content = get_password_reset_template(username, reset_link)
    
    send_email(
        to=to_email,
        subject="Reset Your Password - Cocobase",
        html_content=html_content,
        tags=[
            {"name": "type", "value": "password_reset"},
            {"name": "user", "value": username},
        ]
    )


def send_email_verification_email(username,link,email):
    """
    Send email verification email with secure verification link
    """
    html_content = get_email_verification_template(username,link)

    send_email(
        to=email,
        subject="Verify Your Email - Cocobase",
        html_content=html_content,
        tags=[
            {"name": "type", "value": "email_verification"},
            {"name": "user", "value": username},
        ]
    )