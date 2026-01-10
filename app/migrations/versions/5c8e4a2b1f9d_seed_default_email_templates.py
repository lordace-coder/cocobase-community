"""seed default email templates

Revision ID: 5c8e4a2b1f9d
Revises: 4b15e1fc3bf7
Create Date: 2026-01-10 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5c8e4a2b1f9d'
down_revision: Union[str, None] = '4b15e1fc3bf7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Seed default email templates."""
    from sqlalchemy import text

    connection = op.get_bind()

    # Forgot Password Template
    forgot_password_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .container {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo {
            font-size: 28px;
            font-weight: bold;
            color: #4F46E5;
            margin-bottom: 10px;
        }
        h1 {
            color: #1f2937;
            font-size: 24px;
            margin-bottom: 20px;
        }
        .content {
            margin-bottom: 30px;
        }
        .button {
            display: inline-block;
            padding: 12px 30px;
            background-color: #4F46E5;
            color: #ffffff !important;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
            text-align: center;
        }
        .button:hover {
            background-color: #4338CA;
        }
        .warning {
            background-color: #FEF3C7;
            border-left: 4px solid #F59E0B;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            font-size: 14px;
            color: #6b7280;
            text-align: center;
        }
        .footer a {
            color: #4F46E5;
            text-decoration: none;
        }
        .footer a:hover {
            text-decoration: underline;
        }
        .cocobase-branding {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #e5e7eb;
            font-size: 12px;
            color: #9CA3AF;
        }
        .link {
            color: #4F46E5;
            word-break: break-all;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">{{app_name}}</div>
        </div>

        <h1>Reset Your Password</h1>

        <div class="content">
            <p>Hello,</p>
            <p>We received a request to reset the password for your account. Click the button below to create a new password:</p>

            <div style="text-align: center;">
                <a href="{{reset_link}}" class="button">Reset Password</a>
            </div>

            <p>Or copy and paste this link into your browser:</p>
            <p class="link">{{reset_link}}</p>

            <div class="warning">
                <strong>⚠️ Security Notice:</strong> This link will expire in {{expiry_hours}} hours for security reasons.
            </div>

            <p>If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>
        </div>

        <div class="footer">
            <p>This is an automated message, please do not reply to this email.</p>
            <p>&copy; {{year}} {{app_name}}. All rights reserved.</p>
            <div class="cocobase-branding">
                <p>Powered by <a href="https://cocobase.buzz" style="color: #4F46E5; text-decoration: none;">Cocobase</a> - Backend-as-a-Service</p>
                <p>Build better apps faster with instant APIs, authentication, and more</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    forgot_password_text = """Reset Your Password

Hello,

We received a request to reset the password for your account.

Click the link below to create a new password:
{{reset_link}}

This link will expire in {{expiry_hours}} hours for security reasons.

If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.

---
This is an automated message, please do not reply to this email.
© {{year}} {{app_name}}. All rights reserved.

Powered by Cocobase (https://cocobase.buzz) - Backend-as-a-Service
Build better apps faster with instant APIs, authentication, and more
"""

    # Password Changed Template
    password_changed_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .container {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo {
            font-size: 28px;
            font-weight: bold;
            color: #4F46E5;
            margin-bottom: 10px;
        }
        .success-icon {
            font-size: 48px;
            text-align: center;
            margin: 20px 0;
        }
        h1 {
            color: #1f2937;
            font-size: 24px;
            margin-bottom: 20px;
            text-align: center;
        }
        .content {
            margin-bottom: 30px;
        }
        .info-box {
            background-color: #F3F4F6;
            padding: 15px;
            border-radius: 6px;
            margin: 20px 0;
        }
        .alert {
            background-color: #FEE2E2;
            border-left: 4px solid #DC2626;
            padding: 15px;
            margin: 20px 0;
            border-radius: 4px;
        }
        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            font-size: 14px;
            color: #6b7280;
            text-align: center;
        }
        .footer a {
            color: #4F46E5;
            text-decoration: none;
        }
        .footer a:hover {
            text-decoration: underline;
        }
        .cocobase-branding {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #e5e7eb;
            font-size: 12px;
            color: #9CA3AF;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">{{app_name}}</div>
            <div class="success-icon">✓</div>
        </div>

        <h1>Password Successfully Changed</h1>

        <div class="content">
            <p>Hello,</p>
            <p>This email confirms that your password was successfully changed.</p>

            <div class="info-box">
                <strong>Changed on:</strong> {{change_date}}<br>
                <strong>Time:</strong> {{change_time}}
            </div>

            <div class="alert">
                <strong>⚠️ Didn't make this change?</strong><br>
                If you didn't change your password, please contact support immediately. Your account security may be at risk.
            </div>

            <p>You can now use your new password to sign in to your account.</p>
        </div>

        <div class="footer">
            <p>This is an automated message, please do not reply to this email.</p>
            <p>&copy; {{year}} {{app_name}}. All rights reserved.</p>
            <div class="cocobase-branding">
                <p>Powered by <a href="https://cocobase.buzz" style="color: #4F46E5; text-decoration: none;">Cocobase</a> - Backend-as-a-Service</p>
                <p>Build better apps faster with instant APIs, authentication, and more</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    password_changed_text = """Password Successfully Changed

Hello,

This email confirms that your password was successfully changed.

Changed on: {{change_date}}
Time: {{change_time}}

⚠️ DIDN'T MAKE THIS CHANGE?
If you didn't change your password, please contact support immediately. Your account security may be at risk.

You can now use your new password to sign in to your account.

---
This is an automated message, please do not reply to this email.
© {{year}} {{app_name}}. All rights reserved.

Powered by Cocobase (https://cocobase.buzz) - Backend-as-a-Service
Build better apps faster with instant APIs, authentication, and more
"""

    # Insert templates using raw SQL to handle enum types properly
    import json

    forgot_vars = json.dumps({
        'reset_link': 'The URL link for password reset',
        'expiry_hours': 'Number of hours until the reset link expires',
        'app_name': 'Name of the application',
        'year': 'Current year'
    })

    password_changed_vars = json.dumps({
        'app_name': 'Name of the application',
        'change_date': 'Date when password was changed',
        'change_time': 'Time when password was changed',
        'year': 'Current year'
    })

    # Welcome Email Template
    welcome_html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f4f4f4;
        }
        .container {
            background-color: #ffffff;
            border-radius: 8px;
            padding: 40px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
        }
        .logo {
            font-size: 32px;
            font-weight: bold;
            color: #4F46E5;
            margin-bottom: 20px;
        }
        .welcome-icon {
            font-size: 64px;
            margin: 20px 0;
        }
        h1 {
            color: #1f2937;
            font-size: 28px;
            margin-bottom: 10px;
            text-align: center;
        }
        .subtitle {
            color: #6b7280;
            text-align: center;
            margin-bottom: 30px;
            font-size: 16px;
        }
        .content {
            margin-bottom: 30px;
        }
        .info-box {
            background-color: #EEF2FF;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .button {
            display: inline-block;
            padding: 14px 32px;
            background-color: #4F46E5;
            color: #ffffff !important;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
            text-align: center;
        }
        .button:hover {
            background-color: #4338CA;
        }
        .features {
            margin: 30px 0;
        }
        .feature {
            padding: 15px 0;
            border-bottom: 1px solid #e5e7eb;
        }
        .feature:last-child {
            border-bottom: none;
        }
        .feature-title {
            font-weight: 600;
            color: #1f2937;
            margin-bottom: 5px;
        }
        .footer {
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            font-size: 14px;
            color: #6b7280;
            text-align: center;
        }
        .footer a {
            color: #4F46E5;
            text-decoration: none;
        }
        .footer a:hover {
            text-decoration: underline;
        }
        .cocobase-branding {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #e5e7eb;
            font-size: 12px;
            color: #9CA3AF;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">{{app_name}}</div>
            <div class="welcome-icon">👋</div>
        </div>

        <h1>Welcome to {{app_name}}!</h1>
        <p class="subtitle">We're excited to have you on board</p>

        <div class="content">
            <p>Hello {{user_name}},</p>
            <p>Thank you for creating your account! You're now part of our community.</p>

            <div class="info-box">
                <strong>Your Account Details:</strong><br>
                Email: {{user_email}}<br>
                Joined: {{join_date}}
            </div>

            <div style="text-align: center;">
                <a href="{{login_url}}" class="button">Get Started</a>
            </div>
        </div>

        <div class="footer">
            <p>Need help? Contact our support team anytime.</p>
            <p>&copy; {{year}} {{app_name}}. All rights reserved.</p>
            <div class="cocobase-branding">
                <p>Powered by <a href="https://cocobase.buzz" style="color: #4F46E5; text-decoration: none;">Cocobase</a> - Backend-as-a-Service</p>
                <p>Build better apps faster with instant APIs, authentication, and more</p>
            </div>
        </div>
    </div>
</body>
</html>
"""

    welcome_text = """Welcome to {{app_name}}!

Hello {{user_name}},

We're excited to have you on board! Thank you for creating your account.

Your Account Details:
- Email: {{user_email}}
- Joined: {{join_date}}

Get started: {{login_url}}

Need help? Contact our support team anytime.

---
© {{year}} {{app_name}}. All rights reserved.

Powered by Cocobase (https://cocobase.buzz) - Backend-as-a-Service
Build better apps faster with instant APIs, authentication, and more
"""

    welcome_vars = json.dumps({
        'app_name': 'Name of the application',
        'user_name': 'User\'s name or email',
        'user_email': 'User\'s email address',
        'join_date': 'Date user joined',
        'login_url': 'URL to login page',
        'year': 'Current year'
    })

    # Insert forgot password template
    connection.execute(
        text("""
            INSERT INTO default_email_templates
            (template_type, name, description, subject, html_body, text_body, available_variables, is_active, version, created_at, updated_at)
            VALUES
            (CAST(:template_type AS emailtemplatetypeenum), :name, :description, :subject, :html_body, :text_body, CAST(:available_variables AS json), :is_active, :version, NOW(), NOW())
            ON CONFLICT (template_type) DO NOTHING
        """),
        {
            'template_type': 'FORGOT_PASSWORD',
            'name': 'Forgot Password',
            'description': 'Email sent when user requests a password reset',
            'subject': 'Reset Your Password',
            'html_body': forgot_password_html,
            'text_body': forgot_password_text,
            'available_variables': forgot_vars,
            'is_active': True,
            'version': 1
        }
    )

    # Insert password changed template
    connection.execute(
        text("""
            INSERT INTO default_email_templates
            (template_type, name, description, subject, html_body, text_body, available_variables, is_active, version, created_at, updated_at)
            VALUES
            (CAST(:template_type AS emailtemplatetypeenum), :name, :description, :subject, :html_body, :text_body, CAST(:available_variables AS json), :is_active, :version, NOW(), NOW())
            ON CONFLICT (template_type) DO NOTHING
        """),
        {
            'template_type': 'PASSWORD_CHANGED',
            'name': 'Password Changed Confirmation',
            'description': 'Email sent after a password has been successfully changed',
            'subject': 'Your Password Has Been Changed',
            'html_body': password_changed_html,
            'text_body': password_changed_text,
            'available_variables': password_changed_vars,
            'is_active': True,
            'version': 1
        }
    )

    # Insert welcome template
    connection.execute(
        text("""
            INSERT INTO default_email_templates
            (template_type, name, description, subject, html_body, text_body, available_variables, is_active, version, created_at, updated_at)
            VALUES
            (CAST(:template_type AS emailtemplatetypeenum), :name, :description, :subject, :html_body, :text_body, CAST(:available_variables AS json), :is_active, :version, NOW(), NOW())
            ON CONFLICT (template_type) DO NOTHING
        """),
        {
            'template_type': 'WELCOME',
            'name': 'Welcome Email',
            'description': 'Email sent when a new user signs up',
            'subject': 'Welcome to {{app_name}}!',
            'html_body': welcome_html,
            'text_body': welcome_text,
            'available_variables': welcome_vars,
            'is_active': True,
            'version': 1
        }
    )


def downgrade() -> None:
    """Remove default email templates."""
    op.execute(
        "DELETE FROM default_email_templates WHERE template_type IN ('FORGOT_PASSWORD', 'PASSWORD_CHANGED', 'WELCOME')"
    )
