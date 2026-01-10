"""add_2fa_email_template

Revision ID: d63178d97fb6
Revises: 702a70b369f1
Create Date: 2026-01-10 20:51:38.960846

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd63178d97fb6'
down_revision: Union[str, None] = '702a70b369f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 2FA email template."""
    from sqlalchemy import text
    import json

    connection = op.get_bind()

    # 2FA Verification Code Email Template
    twofa_html = """
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
        .security-icon {
            font-size: 48px;
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
        .code-box {
            background-color: #EEF2FF;
            border: 2px solid #4F46E5;
            border-radius: 8px;
            padding: 30px;
            text-align: center;
            margin: 30px 0;
        }
        .code {
            font-size: 48px;
            font-weight: bold;
            color: #4F46E5;
            letter-spacing: 8px;
            font-family: 'Courier New', monospace;
        }
        .code-label {
            font-size: 14px;
            color: #6b7280;
            margin-top: 10px;
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
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="logo">{{app_name}}</div>
            <div class="security-icon">🔒</div>
        </div>

        <h1>Two-Factor Authentication</h1>

        <div class="content">
            <p>Hello {{user_name}},</p>
            <p>You requested a verification code to sign in to your account. Use the code below to complete your login:</p>

            <div class="code-box">
                <div class="code">{{code}}</div>
                <div class="code-label">Your verification code</div>
            </div>

            <div class="warning">
                <strong>⏰ Time Sensitive:</strong> This code will expire in {{expiry_minutes}} minutes for security reasons.
            </div>

            <p>If you didn't request this code, please ignore this email and ensure your account is secure.</p>
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

    twofa_text = """Two-Factor Authentication

Hello {{user_name}},

You requested a verification code to sign in to your account. Use the code below to complete your login:

VERIFICATION CODE: {{code}}

⏰ This code will expire in {{expiry_minutes}} minutes for security reasons.

If you didn't request this code, please ignore this email and ensure your account is secure.

---
This is an automated message, please do not reply to this email.
© {{year}} {{app_name}}. All rights reserved.

Powered by Cocobase (https://cocobase.buzz) - Backend-as-a-Service
Build better apps faster with instant APIs, authentication, and more
"""

    twofa_vars = json.dumps({
        'app_name': 'Name of the application',
        'user_name': 'User\'s name',
        'code': '6-digit verification code',
        'expiry_minutes': 'Minutes until code expires',
        'year': 'Current year'
    })

    # Insert 2FA template using LOGIN_ALERT enum
    connection.execute(
        text("""
            INSERT INTO default_email_templates
            (template_type, name, description, subject, html_body, text_body, available_variables, is_active, version, created_at, updated_at)
            VALUES
            (CAST(:template_type AS emailtemplatetypeenum), :name, :description, :subject, :html_body, :text_body, CAST(:available_variables AS json), :is_active, :version, NOW(), NOW())
            ON CONFLICT (template_type) DO NOTHING
        """),
        {
            'template_type': 'LOGIN_ALERT',
            'name': '2FA Verification Code',
            'description': 'Email sent with 2FA verification code for login',
            'subject': 'Your Verification Code',
            'html_body': twofa_html,
            'text_body': twofa_text,
            'available_variables': twofa_vars,
            'is_active': True,
            'version': 1
        }
    )


def downgrade() -> None:
    """Remove 2FA email template."""
    op.execute(
        "DELETE FROM default_email_templates WHERE template_type = 'LOGIN_ALERT'"
    )
