# Email Verification for App Users

Complete guide to implementing email verification in your CocoBase application.

---

## 📋 Overview

Email verification ensures that users provide a valid email address during registration. This feature is similar to 2FA and forgot password functionality, providing secure email confirmation for your app users.

### Key Features

- ✅ Automatic verification email on signup (optional)
- ✅ Manual verification email request
- ✅ `email_verified` field in user responses
- ✅ Resend verification email
- ✅ Configurable verification URL
- ✅ 24-hour token expiration
- ✅ OAuth users automatically verified

---

## 🚀 Quick Start

### Step 1: Run Migration

```bash
# Run the migration SQL script
psql -U your_username -d your_database -f EMAIL_VERIFICATION_MIGRATION.sql
```

Or manually:

```sql
-- Add fields to app_users
ALTER TABLE app_users
ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN email_verified_at TIMESTAMP;

-- Create verification tokens table
CREATE TABLE app_users_email_verification_tokens (
    id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    client_id VARCHAR NOT NULL REFERENCES projects(id),
    token VARCHAR UNIQUE NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Add indexes
CREATE INDEX idx_email_verification_tokens_user_id ON app_users_email_verification_tokens(user_id);
CREATE INDEX idx_email_verification_tokens_token ON app_users_email_verification_tokens(token);
```

### Step 2: Enable in Project Config

Enable email verification for your project in the dashboard:

```json
{
  "ENABLE_EMAIL_VERIFICATION": true,
  "VERIFICATION_URL": "https://yourdomain.com/verify-email",
  "FRONTEND_URL": "https://yourdomain.com"
}
```

**Config Options:**
- `ENABLE_EMAIL_VERIFICATION` (boolean): Send verification email on signup
- `VERIFICATION_URL` (string): Full URL where users verify their email
- `FRONTEND_URL` (string): Fallback if VERIFICATION_URL not set

### Step 3: Frontend Integration

Now users will receive verification emails automatically on signup!

---

## 📡 API Endpoints

### 1. Send Verification Email

Send verification email to authenticated user.

**Endpoint:** `POST /auth-collections/verify-email/send`

**Headers:**
```
Authorization: Bearer {user_token}
x-api-key: {project_api_key}
```

**Request:**
```json
{}
```

**Response:**
```json
{
  "message": "Verification email sent successfully. Please check your inbox.",
  "expires_in_hours": 24
}
```

**Example (JavaScript):**
```javascript
async function sendVerificationEmail() {
  const response = await fetch('https://api.cocobase.buzz/auth-collections/verify-email/send', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${userToken}`,
      'x-api-key': 'your-project-api-key',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({})
  });

  const data = await response.json();
  console.log(data.message);
}
```

---

### 2. Verify Email

Verify email using token from verification link.

**Endpoint:** `POST /auth-collections/verify-email/verify`

**Headers:**
```
x-api-key: {project_api_key}
```

**Request:**
```json
{
  "token": "verification_token_from_email_link"
}
```

**Response:**
```json
{
  "message": "Email verified successfully!",
  "email_verified": true,
  "verified_at": "2026-01-13T10:30:00Z"
}
```

**Example (JavaScript):**
```javascript
async function verifyEmail(token) {
  const response = await fetch('https://api.cocobase.buzz/auth-collections/verify-email/verify', {
    method: 'POST',
    headers: {
      'x-api-key': 'your-project-api-key',
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ token })
  });

  const data = await response.json();

  if (data.email_verified) {
    console.log('Email verified successfully!');
    // Redirect to login or dashboard
  }
}

// Get token from URL
const urlParams = new URLSearchParams(window.location.search);
const token = urlParams.get('token');
if (token) {
  verifyEmail(token);
}
```

---

### 3. Resend Verification Email

Resend verification email (alias for /send).

**Endpoint:** `POST /auth-collections/verify-email/resend`

**Headers:**
```
Authorization: Bearer {user_token}
x-api-key: {project_api_key}
```

**Request:**
```json
{}
```

**Response:**
```json
{
  "message": "Verification email sent successfully. Please check your inbox.",
  "expires_in_hours": 24
}
```

---

## 👤 User Response Schema

The `AppUserResponse` schema now includes email verification status:

```json
{
  "id": "user-123",
  "email": "user@example.com",
  "client_id": "project-456",
  "created_at": "2026-01-13T10:00:00Z",
  "roles": ["user"],
  "data": {},
  "email_verified": false,
  "email_verified_at": null
}
```

**Fields:**
- `email_verified` (boolean): Whether email is verified
- `email_verified_at` (datetime | null): When email was verified

---

## 🎨 Frontend Flow Examples

### React Example

#### 1. Check Verification Status

```jsx
import { useState, useEffect } from 'react';

function Dashboard() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    // User data is returned from login/signup
    const userData = JSON.parse(localStorage.getItem('user'));
    setUser(userData);
  }, []);

  if (!user) return <div>Loading...</div>;

  if (!user.email_verified) {
    return <EmailVerificationPrompt user={user} />;
  }

  return <div>Welcome to your dashboard!</div>;
}

function EmailVerificationPrompt({ user }) {
  const [sending, setSending] = useState(false);
  const [message, setMessage] = useState('');

  const resendEmail = async () => {
    setSending(true);
    try {
      const response = await fetch('https://api.cocobase.buzz/auth-collections/verify-email/resend', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'x-api-key': 'your-project-api-key',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
      });

      const data = await response.json();
      setMessage(data.message);
    } catch (error) {
      setMessage('Failed to send email. Please try again.');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="verification-prompt">
      <h2>Verify Your Email</h2>
      <p>Please verify your email address: {user.email}</p>
      <p>Check your inbox for a verification link.</p>

      <button onClick={resendEmail} disabled={sending}>
        {sending ? 'Sending...' : 'Resend Verification Email'}
      </button>

      {message && <p className="message">{message}</p>}
    </div>
  );
}
```

#### 2. Email Verification Page

```jsx
// pages/verify-email.jsx
import { useEffect, useState } from 'react';
import { useRouter } from 'next/router';

function VerifyEmailPage() {
  const router = useRouter();
  const { token } = router.query;
  const [status, setStatus] = useState('verifying'); // verifying, success, error
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (token) {
      verifyEmail(token);
    }
  }, [token]);

  const verifyEmail = async (token) => {
    try {
      const response = await fetch('https://api.cocobase.buzz/auth-collections/verify-email/verify', {
        method: 'POST',
        headers: {
          'x-api-key': 'your-project-api-key',
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ token })
      });

      const data = await response.json();

      if (response.ok) {
        setStatus('success');
        setMessage(data.message);

        // Redirect to login after 3 seconds
        setTimeout(() => {
          router.push('/login');
        }, 3000);
      } else {
        setStatus('error');
        setMessage(data.detail || 'Verification failed');
      }
    } catch (error) {
      setStatus('error');
      setMessage('An error occurred. Please try again.');
    }
  };

  if (status === 'verifying') {
    return (
      <div className="verify-page">
        <h1>Verifying your email...</h1>
        <div className="spinner"></div>
      </div>
    );
  }

  if (status === 'success') {
    return (
      <div className="verify-page success">
        <h1>✅ Email Verified!</h1>
        <p>{message}</p>
        <p>Redirecting to login...</p>
      </div>
    );
  }

  return (
    <div className="verify-page error">
      <h1>❌ Verification Failed</h1>
      <p>{message}</p>
      <a href="/login">Back to Login</a>
    </div>
  );
}

export default VerifyEmailPage;
```

---

### Vue.js Example

```vue
<template>
  <div v-if="!user">
    <p>Loading...</p>
  </div>

  <div v-else-if="!user.email_verified" class="verification-prompt">
    <h2>Verify Your Email</h2>
    <p>Please verify your email address: {{ user.email }}</p>
    <p>Check your inbox for a verification link.</p>

    <button @click="resendEmail" :disabled="sending">
      {{ sending ? 'Sending...' : 'Resend Verification Email' }}
    </button>

    <p v-if="message" class="message">{{ message }}</p>
  </div>

  <div v-else>
    <h1>Welcome to your dashboard!</h1>
  </div>
</template>

<script>
export default {
  data() {
    return {
      user: null,
      sending: false,
      message: ''
    };
  },

  mounted() {
    const userData = JSON.parse(localStorage.getItem('user'));
    this.user = userData;
  },

  methods: {
    async resendEmail() {
      this.sending = true;
      this.message = '';

      try {
        const response = await fetch('https://api.cocobase.buzz/auth-collections/verify-email/resend', {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`,
            'x-api-key': 'your-project-api-key',
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({})
        });

        const data = await response.json();
        this.message = data.message;
      } catch (error) {
        this.message = 'Failed to send email. Please try again.';
      } finally {
        this.sending = false;
      }
    }
  }
};
</script>
```

---

## 🔒 Security Features

### 1. Token Expiration

Verification tokens expire after 24 hours for security.

### 2. Rate Limiting

- Only one verification email can be sent every 5 minutes per user
- Prevents spam and abuse

### 3. One-Time Use

- Tokens can only be used once
- Marked as `is_used=true` after verification

### 4. OAuth Auto-Verification

Users who sign up via OAuth (Google, Apple, GitHub) are automatically marked as verified since OAuth providers verify email addresses.

---

## ⚙️ Configuration Options

### Project Config (in Dashboard)

```json
{
  "ENABLE_EMAIL_VERIFICATION": true,
  "VERIFICATION_URL": "https://yourdomain.com/verify-email",
  "FRONTEND_URL": "https://yourdomain.com",
  "SEND_WELCOME_EMAIL": true
}
```

**Options:**

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `ENABLE_EMAIL_VERIFICATION` | boolean | false | Send verification email on signup |
| `VERIFICATION_URL` | string | null | Full URL for verification page |
| `FRONTEND_URL` | string | null | Fallback URL (appends /verify-email) |
| `SEND_WELCOME_EMAIL` | boolean | true | Send welcome email on signup |

---

## 📧 Email Template

The system uses the `VERIFICATION` template type. Make sure you have a verification email template configured in your project.

**Default Template Variables:**

- `{{user_name}}` - User's name
- `{{app_name}}` - Your app name
- `{{verification_url}}` - Full verification link with token
- `{{expiry_hours}}` - Hours until token expires (24)

**Example Email Template:**

```html
<!DOCTYPE html>
<html>
<head>
    <title>Verify Your Email</title>
</head>
<body>
    <h1>Welcome to {{app_name}}, {{user_name}}!</h1>

    <p>Please verify your email address by clicking the button below:</p>

    <a href="{{verification_url}}" style="display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">
        Verify Email
    </a>

    <p>Or copy and paste this link into your browser:</p>
    <p>{{verification_url}}</p>

    <p>This link will expire in {{expiry_hours}} hours.</p>

    <p>If you didn't create an account, you can safely ignore this email.</p>
</body>
</html>
```

---

## 🧪 Testing

### Test Flow

1. **Sign up a new user**
   ```bash
   curl -X POST https://api.cocobase.buzz/auth-collections/signup \
     -H "x-api-key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"email": "test@example.com", "password": "password123"}'
   ```

2. **Check user response** - should have `email_verified: false`

3. **Request verification email**
   ```bash
   curl -X POST https://api.cocobase.buzz/auth-collections/verify-email/send \
     -H "Authorization: Bearer {token}" \
     -H "x-api-key: your-api-key"
   ```

4. **Get token from email** (or database for testing)

5. **Verify email**
   ```bash
   curl -X POST https://api.cocobase.buzz/auth-collections/verify-email/verify \
     -H "x-api-key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"token": "token-from-email"}'
   ```

6. **Check user again** - should have `email_verified: true`

---

## 🔧 Troubleshooting

### Issue: Verification email not received

**Check:**
1. Email provider configured in project settings
2. `ENABLE_EMAIL_VERIFICATION` set to true in project config
3. Check spam folder
4. Verify email logs in database

### Issue: Token expired

**Solution:**
- Tokens expire after 24 hours
- Request a new verification email using `/resend` endpoint

### Issue: Invalid token error

**Check:**
1. Token hasn't been used already
2. Token belongs to correct project
3. Token hasn't expired

### Issue: email_verified field not in response

**Solution:**
- Run the migration script to add fields to database
- Restart your application

---

## 🚀 Migration from Existing Users

If you have existing users and want to add email verification:

### Option 1: Mark all existing users as verified

```sql
UPDATE app_users
SET email_verified = TRUE,
    email_verified_at = NOW()
WHERE email_verified = FALSE;
```

### Option 2: Require verification for all

1. Don't run the above query
2. Existing users will need to verify their emails
3. Send bulk verification emails using a script

### Option 3: Gradual rollout

```sql
-- Mark OAuth users as verified only
UPDATE app_users
SET email_verified = TRUE,
    email_verified_at = created_at
WHERE oauth_provider IS NOT NULL AND email_verified = FALSE;
```

---

## 📊 Database Schema

### app_users table (new fields)

```sql
email_verified BOOLEAN NOT NULL DEFAULT FALSE
email_verified_at TIMESTAMP
```

### app_users_email_verification_tokens table

```sql
id VARCHAR PRIMARY KEY
user_id VARCHAR NOT NULL
client_id VARCHAR NOT NULL REFERENCES projects(id)
token VARCHAR UNIQUE NOT NULL
expires_at TIMESTAMP NOT NULL
is_used BOOLEAN NOT NULL DEFAULT FALSE
created_at TIMESTAMP DEFAULT NOW()
```

---

## 🎯 Best Practices

1. **Always check email_verified on frontend**
   - Show verification prompt if not verified
   - Restrict certain features until verified

2. **Clear messaging**
   - Tell users to check spam folder
   - Show resend button prominently

3. **Handle edge cases**
   - Token expired → allow resend
   - Email already verified → show success message
   - Invalid token → show clear error

4. **OAuth users**
   - Already marked as verified automatically
   - No verification needed

5. **Security**
   - Never expose tokens in logs
   - Use HTTPS for verification URLs
   - Implement rate limiting

---

## ✅ Summary

Email verification is now fully integrated into your CocoBase application!

**What you get:**
- ✅ Automatic verification emails on signup
- ✅ Manual verification request endpoint
- ✅ Email verification status in all user responses
- ✅ Secure token-based verification
- ✅ OAuth users automatically verified
- ✅ Resend functionality
- ✅ Configurable per project

**Next steps:**
1. Run the migration
2. Enable in project config
3. Create verification page in your frontend
4. Test the flow

---

**Need help?** Check the troubleshooting section or reach out to support!
