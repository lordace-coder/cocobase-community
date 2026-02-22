# Auth Response Types

Quick reference for all authentication endpoint responses.

## Login / Signup / OAuth

### Success (normal)
```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "user": {
    "id": "uuid",
    "email": "user@example.com",
    "data": {},
    "roles": [],
    "email_verified": false,
    "email_verified_at": null,
    "created_at": "2024-01-01T00:00:00"
  }
}
```

### 2FA Required
```json
{
  "requires_2fa": true,
  "message": "2FA code sent to your email"
}
```

---

## 2FA Verify (`POST /auth-collections/2fa/verify`)

### Success
```json
{
  "access_token": "eyJhbGciOiJIUzI1...",
  "user": { ... },
  "message": "2FA verification successful"
}
```

### Error
```json
{ "detail": "Invalid email or code" }
```

---

## Email Verification

### Send (`POST /auth-collections/verify-email/send`)
```json
{
  "message": "Verification email sent successfully. Please check your inbox.",
  "expires_in_hours": 24
}
```

### Verify (`POST /auth-collections/verify-email/verify`)
```json
{
  "message": "Email verified successfully!",
  "email_verified": true,
  "verified_at": "2024-01-01T00:00:00"
}
```

---

## Password Reset

### Forgot (`POST /auth-collections/forgot-password`)
```json
{ "message": "If that email exists, a reset link has been sent" }
```

### Reset (`POST /auth-collections/reset-password`)
```json
{ "message": "Password successfully reset" }
```

---

## 2FA Management

### Enable (`POST /auth-collections/2fa/enable`)
```json
{ "message": "2FA enabled successfully" }
```

### Disable (`POST /auth-collections/2fa/disable`)
```json
{ "message": "2FA disabled successfully" }
```

### Send Code (`POST /auth-collections/2fa/send-code`)
```json
{ "message": "2FA code sent" }
```

---

## TypeScript Types

```typescript
interface AuthUser {
  id: string;
  email: string;
  data?: Record<string, any>;
  roles?: string[];
  email_verified: boolean;
  email_verified_at?: string | null;
  created_at: string;
  oauth_provider?: string;
}

interface LoginResponse {
  access_token?: string;
  user?: AuthUser;
  requires_2fa?: boolean;
  message?: string;
}

interface TwoFAVerifyResponse {
  access_token: string;
  user: AuthUser;
  message: string;
}

interface EmailVerificationSendResponse {
  message: string;
  expires_in_hours: number;
}

interface EmailVerificationVerifyResponse {
  message: string;
  email_verified: boolean;
  verified_at: string;
}

interface MessageResponse {
  message: string;
}
```
