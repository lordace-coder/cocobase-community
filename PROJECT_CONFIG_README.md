# CocoBase Project Configuration Guide

This document describes all the configuration options available for your CocoBase project.

## Project Settings (`project.configs`)

These settings are stored in your project's `configs` JSON field and can be set via the dashboard or API.

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `FRONTEND_URL` | `string` | - | Your frontend application URL. Used as fallback for email redirects and OAuth callbacks. |
| `LOGIN_URL` | `string` | - | URL to your login page. Included in welcome emails and password reset pages. |
| `VERIFICATION_URL` | `string` | - | Custom URL for email verification links. If not set, uses CocoBase's built-in verification page. |
| `VERIFICATION_SUCCESS_URL` | `string` | - | URL to redirect users after successful email verification. Falls back to `FRONTEND_URL` if not set. |
| `PASSWORD_RESET_URL` | `string` | - | Custom URL for password reset page. If not set, uses CocoBase's built-in reset page. |
| `SEND_WELCOME_EMAIL` | `boolean` | `true` | Send welcome email when a new user signs up. |
| `ENABLE_EMAIL_VERIFICATION` | `boolean` | `false` | Automatically send verification email on signup. |
| `ENABLE_2FA` | `boolean` | `false` | Enable two-factor authentication for your project. Users can then opt-in to 2FA. |
| `OTP_LENGTH` | `integer` | `6` | Length of OTP codes for 2FA and phone login (4-10 digits). |
| `ENABLE_PHONE_LOGIN` | `boolean` | `false` | Enable login with phone number via OTP for all users in the project. |
| `ALLOWED_SELF_ROLES` | `array` | - | List of roles users can assign to themselves during signup/update. If not set, users can assign any role. |

## Authentication Settings

### Welcome Email

By default, CocoBase sends a welcome email when a new user signs up.

**Configurable Options:**
| Config | Type | Default | Description |
|--------|------|---------|-------------|
| `SEND_WELCOME_EMAIL` | `boolean` | `true` | Send welcome email on signup |
| `LOGIN_URL` | `string` | - | Login URL included in the welcome email |

Set `SEND_WELCOME_EMAIL` to `false` to disable welcome emails.

### Email Verification

When a user signs up, their `email_verified` field is set to `false`. You can verify emails in two ways:

**Option 1: Automatic verification on signup**
Set `ENABLE_EMAIL_VERIFICATION` to `true` to automatically send verification emails when users sign up.

**Option 2: Manual verification**
Call `POST /auth-collections/verify-email/send` to send a verification email to the authenticated user.

**Configurable Options:**
| Config | Type | Default | Description |
|--------|------|---------|-------------|
| `ENABLE_EMAIL_VERIFICATION` | `boolean` | `false` | Auto-send verification email on signup |
| `VERIFICATION_URL` | `string` | CocoBase hosted page | Custom URL for verification links |
| `VERIFICATION_SUCCESS_URL` | `string` | - | Redirect URL after successful verification |

**Verification URL Behavior:**
- If `VERIFICATION_URL` is set: Links point to your custom URL with `?token={token}`
- If `FRONTEND_URL` is set (no `VERIFICATION_URL`): Links point to your frontend with `?token={token}`
- If neither is set: Links point to `https://api.cocobase.buzz/verify-email?token={token}` (built-in verification page)

### Password Reset

Users can request a password reset via `POST /auth-collections/forgot-password`.

**Configurable Options:**
| Config | Type | Default | Description |
|--------|------|---------|-------------|
| `PASSWORD_RESET_URL` | `string` | CocoBase hosted page | Custom URL for password reset. Token appended as `?token={token}` |
| `LOGIN_URL` | `string` | - | URL to redirect users after successful reset |

**Reset URL Behavior:**
- If `PASSWORD_RESET_URL` is set: Links point to your custom URL with `?token={token}`
- If not set: Links point to `https://api.cocobase.buzz/auth-collections/reset-password-page?token={token}` (built-in page)

### Two-Factor Authentication (2FA)

2FA can be enabled per project via the `ENABLE_2FA` config. When enabled:
- Users can opt-in to 2FA via `POST /auth-collections/2fa/enable`
- Users receive an OTP code via email during login
- Codes expire after 10 minutes
- Users must provide the code to complete authentication

**Configurable Options:**
| Config | Type | Default | Description |
|--------|------|---------|-------------|
| `ENABLE_2FA` | `boolean` | `false` | Enable 2FA for the project |
| `OTP_LENGTH` | `integer` | `6` | OTP code length (4-10 digits) |

**Example:**
```json
{
  "ENABLE_2FA": true,
  "OTP_LENGTH": 8
}
```

### Phone Authentication

Enable phone number login for your project via `ENABLE_PHONE_LOGIN`. When enabled:
- Users can add a phone number to their account via `POST /auth-collections/phone/update`
- Users can verify their phone via `POST /auth-collections/phone/send-otp` and `POST /auth-collections/phone/verify-otp`
- Users can login with phone + OTP via `POST /auth-collections/phone/login/send-otp` and `POST /auth-collections/phone/login`
- Phone verification is **optional** - users can login with unverified phone numbers

**Configurable Options:**
| Config | Type | Default | Description |
|--------|------|---------|-------------|
| `ENABLE_PHONE_LOGIN` | `boolean` | `false` | Enable phone login for the project |
| `OTP_LENGTH` | `integer` | `6` | OTP code length (4-10 digits) |

**Phone Login Flow:**
1. User adds phone number: `POST /auth-collections/phone/update` (requires password)
2. (Optional) User verifies phone: `POST /auth-collections/phone/send-otp` → `POST /auth-collections/phone/verify-otp`
3. Login: `POST /auth-collections/phone/login/send-otp` → `POST /auth-collections/phone/login`

**Important:** The OTP code is returned in the response for you to send via SMS. CocoBase does not send SMS directly.

**Example Response from send-otp:**
```json
{
  "message": "OTP generated successfully. Send this code via SMS.",
  "phone_number": "+1234567890",
  "code": "123456",
  "expires_in_minutes": 10
}
```

### User Roles

Users can have roles assigned to them. You can control which roles users can assign to themselves via the `ALLOWED_SELF_ROLES` config.

**Configurable Options:**
| Config | Type | Default | Description |
|--------|------|---------|-------------|
| `ALLOWED_SELF_ROLES` | `array` | - | Roles users can self-assign during signup/update |

**Behavior:**
- If `ALLOWED_SELF_ROLES` is not set: Users can assign any role to themselves (backwards compatible)
- If `ALLOWED_SELF_ROLES` is set: Users can only assign roles from this list

**Example (array format):**
```json
{
  "ALLOWED_SELF_ROLES": ["buyer", "seller", "creator"]
}
```

**Example (string format):**
```json
{
  "ALLOWED_SELF_ROLES": "buyer, seller, creator"
}
```

With this config, if a user tries to signup with roles `["buyer", "admin"]`, only `["buyer"]` will be assigned since `admin` is not in the allowed list.

**Security Note:** Protected roles like `admin` should NOT be included in `ALLOWED_SELF_ROLES`. Admin roles should only be assigned server-side or via the dashboard.

## Email Configuration

### SMTP Settings

Configure custom SMTP settings for your project via the dashboard or API. Settings include:

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `host` | `string` | - | SMTP server hostname (e.g., `smtp.gmail.com`) |
| `port` | `integer` | `587` | SMTP port |
| `username` | `string` | - | SMTP authentication username |
| `password` | `string` | - | SMTP authentication password |
| `use_tls` | `boolean` | `true` | Enable TLS encryption |
| `use_ssl` | `boolean` | `false` | Enable SSL encryption |
| `from_email` | `string` | - | Sender email address |
| `from_name` | `string` | - | Sender display name |
| `daily_limit` | `integer` | `null` | Optional daily email limit |
| `hourly_limit` | `integer` | `null` | Optional hourly email limit |

If no SMTP is configured, CocoBase uses its default email service.

### Email Templates

Customize email templates for various events:

| Template Type | Description | Available Variables |
|---------------|-------------|---------------------|
| `WELCOME` | Sent when a new user signs up | `user_name`, `app_name` |
| `VERIFICATION` | Email verification link | `user_name`, `app_name`, `verification_url`, `expiry_hours` |
| `FORGOT_PASSWORD` | Password reset request | `user_name`, `app_name`, `reset_url`, `expiry_hours` |
| `RESET_PASSWORD` | Password reset confirmation | `user_name`, `app_name` |
| `PASSWORD_CHANGED` | Password change notification | `user_name`, `app_name` |
| `LOGIN_ALERT` | Login from new device/location | `user_name`, `app_name`, `login_time`, `device_info` |
| `CUSTOM` | Custom templates | Your defined variables |

Templates support Jinja2 syntax: `{{ variable_name }}`

## OAuth Configuration

### Google OAuth (for App Users)

To enable Google Sign-In for your app users, configure via the OAuth settings:

1. Create a Google OAuth client in Google Cloud Console
2. Add your OAuth credentials via the dashboard
3. Configure redirect URIs in Google Console

## Collection Permissions

Set granular permissions on collections:

```json
{
  "create": ["authenticated", "role:admin"],
  "read": ["*"],
  "update": ["owner", "role:admin"],
  "delete": ["role:admin"]
}
```

**Permission Types:**
- `*` - Anyone (public access)
- `authenticated` - Any authenticated user
- `owner` - Only the record owner (requires `_owner` field)
- `role:rolename` - Users with specific role

## API Rate Limits

Rate limits are determined by your subscription plan:

| Plan | ORM Requests/min | Max Storage | Max Users | Max Cloud Functions |
|------|------------------|-------------|-----------|---------------------|
| Free | 100 | Plan limit | Plan limit | Plan limit |
| Starter | 500 | Plan limit | Plan limit | Plan limit |
| Pro | 2000 | Plan limit | Plan limit | Plan limit |
| Enterprise | 5000 | Plan limit | Plan limit | Plan limit |

## Storage Configuration

Storage limits are per-project based on your plan. Files are stored in Backblaze B2 (S3-compatible).

**Storage API:**
- `POST /storage/upload` - Upload files
- `GET /storage/files` - List files
- `DELETE /storage/files/{file_id}` - Delete files

## Cloud Functions

Write serverless functions that run in response to events or HTTP requests.

**Supported Runtimes:**
- `python3.10`
- `node18`
- `go1.20`

**Execution Limits:**
- Timeout: 20 seconds
- Memory: Based on plan

## Webhooks

Configure webhooks to receive notifications for events:

- Collection record changes (create, update, delete)
- User authentication events
- Payment events

**Webhook Payload:**
```json
{
  "event": "collection.create",
  "project_id": "...",
  "collection": "...",
  "data": {...},
  "timestamp": "..."
}
```

## Allowed Origins (CORS)

Configure which domains can access your project's API:

```json
{
  "allowed_origins": [
    "https://myapp.com",
    "https://staging.myapp.com",
    "http://localhost:3000"
  ]
}
```

Set via dashboard or API. Use `["*"]` to allow all origins (not recommended for production).

## Callback URL

Set a callback URL for OAuth flows and other redirects:

```
callback_url: "https://myapp.com/auth/callback"
```

## JWT Token Configuration

**App User Tokens:**
- Access tokens expire in 2 days
- Use refresh tokens for longer sessions

**Token Claims:**
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "client_id": "project_id",
  "roles": ["user"],
  "exp": "...",
  "iat": "..."
}
```
