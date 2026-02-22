# Password Reset Feature - Complete Implementation

## Overview

The forgot password feature is fully implemented with **two options**:

1. **Default (Recommended)**: Cocobase handles everything - just works out of the box
2. **Custom**: Users can host their own password reset page for full branding control

### Zero Configuration Required! 🎉

The password reset feature works immediately without ANY setup:
- ✅ **No email provider needed** - Uses Cocobase's Resend account automatically
- ✅ **Professional email templates** - Already seeded in database
- ✅ **Hosted reset page** - Cocobase provides the UI
- ✅ **Complete flow** - From request to confirmation email

Your users can start using forgot password right away!

---

## Default Flow (Cocobase Handles Everything)

### User Experience
1. User clicks "Forgot Password" on their app
2. App calls `/auth-collections/forgot-password` with user's email
3. User receives professional email with reset link
4. User clicks link → lands on Cocobase-hosted reset page
5. User enters new password
6. Password is updated automatically
7. User receives confirmation email
8. User is redirected to login (if configured)

### For Your Users (Project Owners)
**No configuration needed!** It just works.

**Optional Configuration:**
```python
project.configs = {
    "LOGIN_URL": "https://yourapp.com/login"  # Where to redirect after success
}
```

### Implementation Files
- **Page**: [app/templates/reset_password.html](app/templates/reset_password.html)
- **Route**: [app/api/app_user_password_reset.py:22-78](app/api/app_user_password_reset.py#L22-L78) - `GET /auth-collections/reset-password-page`
- **API**: [app/api/app_user_password_reset.py:111-148](app/api/app_user_password_reset.py#L111-L148) - `POST /auth-collections/reset-password`

---

## Custom Flow (Users Host Their Own Page)

### User Experience
1. User clicks "Forgot Password" on their app
2. App calls `/auth-collections/forgot-password` with user's email
3. User receives professional email with reset link **to their custom page**
4. User clicks link → lands on **their branded reset page**
5. User enters new password
6. Their page calls Cocobase API to update password
7. User receives confirmation email

### For Your Users (Project Owners)
**Configuration Required:**
```python
project.configs = {
    "PASSWORD_RESET_URL": "https://yourapp.com/reset-password",  # Your custom page
    "LOGIN_URL": "https://yourapp.com/login"  # Optional: redirect after success
}
```

**Example Template**: [examples/custom_password_reset_page_example.html](examples/custom_password_reset_page_example.html)

---

## API Endpoints

### 1. Request Password Reset
```http
POST /auth-collections/forgot-password
Content-Type: application/json
X-API-Key: {project_api_key}

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

**Security:** Always returns 200 to prevent email enumeration

---

### 2. Get Reset Password Page (Cocobase-Hosted)
```http
GET /auth-collections/reset-password-page?token={reset_token}
```

**Response:** HTML page for resetting password

**Features:**
- Auto-populates project name and branding
- Client-side password validation
- Automatic API key injection
- Redirect to login after success (if configured)
- Professional error handling

---

### 3. Reset Password (API)
```http
POST /auth-collections/reset-password
Content-Type: application/json
X-API-Key: {project_api_key}

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

**Actions:**
- Validates token (not expired, not used)
- Updates user password (hashed)
- Marks token as used
- Sends confirmation email

---

## Email Templates

### Forgot Password Email
- **Template Type**: `FORGOT_PASSWORD`
- **Subject**: "Reset Your Password"
- **Variables**: `{{reset_link}}`, `{{app_name}}`, `{{expiry_hours}}`, `{{year}}`
- **Features**: Professional HTML design, security warning, expiry notice

### Password Changed Email
- **Template Type**: `PASSWORD_CHANGED`
- **Subject**: "Your Password Has Been Changed"
- **Variables**: `{{app_name}}`, `{{change_date}}`, `{{change_time}}`, `{{year}}`
- **Features**: Timestamp info, security alert if unauthorized

**Templates can be overridden** per project by creating a `ProjectEmailTemplate`

---

## Configuration Options

All config keys use UPPERCASE (like environment variables):

| Config Key | Type | Description | Default |
|------------|------|-------------|---------|
| `PASSWORD_RESET_URL` | string | Custom URL for password reset page | `https://api.cocobase.buzz/auth-collections/reset-password-page` |
| `LOGIN_URL` | string | Where to redirect after successful reset | `null` (shows success message) |

### Example Configuration
```python
from app.models.app_client import Project
from app.core.database import get_db

db = next(get_db())
project = db.query(Project).filter(Project.id == "project_id").first()

# Update configuration
project.configs = {
    **project.configs,  # Preserve existing configs
    "PASSWORD_RESET_URL": "https://myapp.com/reset",
    "LOGIN_URL": "https://myapp.com/login"
}
db.commit()
```

---

## Email Provider Fallback System

Cocobase uses a **three-tier priority system** for sending emails:

### Priority 1: Project Integration
If a project has configured an email integration (Resend, Cocomailer, or EmailJS), that will be used.

### Priority 2: SMTP Configuration
If no integration but SMTP is configured, SMTP will be used.

### Priority 3: Cocobase Fallback (Automatic)
If nothing is configured, Cocobase automatically uses its own Resend account:
- **From**: `Cocobase <noreply@cocobase.buzz>`
- **Provider**: Resend
- **API Key**: `COCOBASE_RESEND_API_KEY` environment variable

This means:
- ✅ **Zero configuration needed** for testing
- ✅ **Production-ready** - users can start immediately
- ✅ **Seamless upgrade** - configure email provider anytime

### Environment Variables
```bash
# Required for fallback email (already in .env)
COCOBASE_RESEND_API_KEY=your_resend_api_key
```

---

## Security Features

1. **Email Enumeration Prevention**: Always returns success response
2. **Token Expiration**: Tokens expire after 24 hours (configurable)
3. **One-Time Use**: Tokens marked as used after successful reset
4. **Confirmation Email**: Users receive email when password changes
5. **Password Hashing**: Passwords hashed using secure algorithms
6. **HTTPS Required**: All reset links use HTTPS
7. **Client-Side Validation**: Password requirements enforced

---

## File Structure

```
app/
├── api/
│   └── app_user_password_reset.py      # All password reset endpoints
├── templates/
│   └── reset_password.html             # Cocobase-hosted reset page
├── services/
│   └── email_service.py                # Email sending with templates
├── models/
│   └── email_models.py                 # Email template models
└── migrations/
    └── versions/
        └── 5c8e4a2b1f9d_*.py           # Default templates seeding

examples/
└── custom_password_reset_page_example.html  # Example for custom implementation

docs/
├── FORGOT_PASSWORD_SETUP.md            # Detailed setup guide
└── PASSWORD_RESET_SUMMARY.md           # This file
```

---

## Testing Checklist

- [ ] User can request password reset via API
- [ ] Email is sent with correct reset link
- [ ] Default Cocobase page loads with token
- [ ] Password can be reset on Cocobase page
- [ ] Confirmation email is sent after reset
- [ ] Invalid tokens show proper error
- [ ] Expired tokens cannot be used
- [ ] Used tokens cannot be reused
- [ ] Custom `PASSWORD_RESET_URL` works
- [ ] Custom `LOGIN_URL` redirect works
- [ ] Email templates can be overridden
- [ ] Email logging tracks all attempts

---

## Migration

Run the migration to seed default email templates:

```bash
alembic upgrade head
```

This creates the two default templates:
- `FORGOT_PASSWORD`
- `PASSWORD_CHANGED`

---

## For End Users (Your Customers)

When your customers build apps with Cocobase:

### Zero Configuration (Easiest)
Just use the forgot password feature - everything works automatically with professional emails and a branded reset page.

### Custom Branding (Advanced)
1. Create your own password reset page using our example template
2. Host it on your domain
3. Add one line of config: `PASSWORD_RESET_URL`
4. Done! Emails will link to your page instead

---

## Support

- **Documentation**: [FORGOT_PASSWORD_SETUP.md](FORGOT_PASSWORD_SETUP.md)
- **Example Template**: [examples/custom_password_reset_page_example.html](examples/custom_password_reset_page_example.html)
- **API Reference**: See API Endpoints section above
