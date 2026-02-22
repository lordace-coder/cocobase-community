import os
from jinja2 import Environment, FileSystemLoader, select_autoescape

# Configure Jinja2 environment
template_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")

jinja_env = Environment(
    loader=FileSystemLoader(template_dir), autoescape=select_autoescape(["html", "xml"])
)


def get_email_template(title: str, message: str) -> str:
    """
    Get generic email template

    Args:
        title: Email title/heading
        message: Email message content

    Returns:
        str: Rendered HTML content
    """
    template = jinja_env.get_template("emails/basic_email.html")
    return template.render(title=title, message=message)


def get_email_verification_template(username: str, link: str) -> str:
    """
    Get email verification template

    Args:
        username: User's display name
        link: Verification link URL

    Returns:
        str: Rendered HTML content
    """
    template = jinja_env.get_template("emails/email_verification.html")
    return template.render(username=username, verification_link=link)


def get_password_reset_template(username: str, reset_link: str) -> str:
    """
    Get password reset template

    Args:
        username: User's display name
        reset_link: Password reset link URL

    Returns:
        str: Rendered HTML content
    """
    template = jinja_env.get_template("emails/password_reset.html")
    return template.render(username=username, reset_link=reset_link)
