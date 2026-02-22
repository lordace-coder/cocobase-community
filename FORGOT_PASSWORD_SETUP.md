# Forgot Password Feature Setup

## Overview
The forgot password feature allows users to reset their passwords via email using customizable templates.

## Setup Steps

### 1. Run the Migration
Execute the migration to seed the default email templates:

```bash
alembic upgrade head
```

This will create two default email templates:
- **Forgot Password**: Sent when user requests a password reset
- **Password Changed**: Confirmation email after successful password change

### 2. Email Provider (Optional!)

**Good News:** Email works out of the box! If your project doesn't have an email provider configured, Cocobase will automatically use its own Resend account (`noreply@cocobase.buzz`) to send password reset emails.

**Priority Order:**
1. **Project Integration** (Resend, Cocomailer, EmailJS) - if configured
2. **SMTP Configuration** - if configured
3. **Cocobase Fallback** - automatic (uses `noreply@cocobase.buzz`)

This means users can test the forgot password feature immediately without any email setup!

## API Endpoints

### Request Password Reset
```http
POST /auth-collections/forgot-password
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "message": "If that email exists, a reset link has been sent"
}
```

**Note:** Always returns 200 to prevent email enumeration attacks.

### Reset Password
```http
POST /auth-collections/reset-password
Content-Type: application/json

{
  "token": "reset_token_here",
  "new_password": "newSecurePassword123"
}
```

**Response:**
```json
{
  "message": "Password successfully reset"
}
```

## Email Templates

### Default Templates
The system comes with two default email templates:

1. **Forgot Password Template**
   - Subject: "Reset Your Password"
   - Variables: `{{reset_link}}`, `{{app_name}}`, `{{expiry_hours}}`, `{{year}}`

2. **Password Changed Template**
   - Subject: "Your Password Has Been Changed"
   - Variables: `{{app_name}}`, `{{change_date}}`, `{{change_time}}`, `{{year}}`

### Template Override
Projects can override default templates by creating a `ProjectEmailTemplate` with the same `template_type`:

```python
from app.models.email_models import ProjectEmailTemplate, EmailTemplateTypeEnum

project_template = ProjectEmailTemplate(
    project_id="your_project_id",
    template_type=EmailTemplateTypeEnum.FORGOT_PASSWORD,
    name="Custom Forgot Password",
    subject="Custom Subject",
    html_body="<html>...</html>",
    text_body="Plain text version",
    is_active=True
)
```

### Template Priority
1. **Project-specific template** (if exists and is active)
2. **Default template** (fallback)

## Email Logging
All emails are logged in the `email_logs` table with:
- Recipients
- Subject
- Template type
- Status (pending, sent, failed)
- Timestamp
- Error messages (if failed)

## How It Works

### Default Flow (Cocobase Handles Everything)

By default, Cocobase handles the entire password reset flow:

1. User requests password reset via `/forgot-password` endpoint
2. Cocobase sends email with link to Cocobase-hosted reset page
3. Email contains: `https://api.cocobase.buzz/auth-collections/reset-password-page?token=abc123`
4. User clicks link and sees the **Cocobase-hosted reset password page**
5. User enters new password on the page
6. Page calls the `/reset-password` API endpoint automatically
7. User receives confirmation email

**No configuration needed!** This works out of the box.

### Optional: Use Your Own Reset Page

If you want to use your own custom UI, configure the project's `PASSWORD_RESET_URL`:

```python
# Update project config (use UPPERCASE like environment variables)
project.configs = {
    ...project.configs,
    "PASSWORD_RESET_URL": "https://your-app.com/reset-password",
    "LOGIN_URL": "https://your-app.com/login"  # Optional: where to redirect after success
}
db.commit()
```

**How the custom flow works:**
1. User requests password reset via `/forgot-password` endpoint
2. The token is generated and the email is sent to the user
3. The email contains a link to YOUR page: `https://your-app.com/reset-password?token=abc123`
4. User clicks the link and lands on **your frontend page**
5. Your frontend page extracts the token from the URL query parameter
6. User enters their new password on your page
7. Your frontend calls the `/reset-password` API endpoint with the token and new password

## Configuration Options

All configuration keys should be UPPERCASE (like environment variables):

| Config Key | Description | Default |
|------------|-------------|---------|
| `PASSWORD_RESET_URL` | Custom URL for password reset page | `https://api.cocobase.buzz/auth-collections/reset-password-page` |
| `LOGIN_URL` | Where to redirect after successful reset | None (shows success message) |

### Frontend Integration Example

Your frontend page should:

```javascript
// 1. Extract token from URL
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');

// 2. When user submits new password
async function resetPassword(newPassword) {
    const response = await fetch('https://api.cocobase.buzz/auth-collections/reset-password', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': 'your-project-api-key'
        },
        body: JSON.stringify({
            token: token,
            new_password: newPassword
        })
    });

    if (response.ok) {
        // Show success message and redirect to login
        alert('Password reset successfully!');
        window.location.href = '/login';
    } else {
        // Handle error (invalid/expired token, etc.)
        alert('Failed to reset password. Please try again.');
    }
}
```

### Modify Template Variables
Update the context dictionary in `EmailService.send_password_reset_email()`:

```python
context = {
    "reset_link": reset_link,
    "app_name": app_name,
    "expiry_hours": expiry_hours,
    "year": datetime.now().year,
    # Add custom variables here
}
```

## Security Features

1. **Email Enumeration Prevention**: Always returns success response
2. **Token Expiration**: Tokens expire after configured hours (default: 24h)
3. **One-time Use**: Tokens are marked as used after successful reset
4. **Confirmation Email**: Users receive confirmation when password is changed
5. **Password Hashing**: Passwords are hashed using secure algorithms

## Troubleshooting

### Email Not Sending
1. Check if email provider is configured and active
2. Verify email templates exist in database
3. Check `email_logs` table for error messages
4. Ensure project has correct email integration settings

### Template Not Found Error
Run the migration to seed default templates:
```bash
alembic upgrade head
```

### User Not Receiving Email
1. Check spam/junk folder
2. Verify email provider credentials
3. Check email logs for delivery status
4. Ensure recipient email is correct
