# CocoBase ORM Microservice Specification

**Version:** 1.0
**Language:** Go (Golang)
**Purpose:** Provide secure, language-agnostic database access to CocoBase users through a REST API

---

## 🎯 Overview

The CocoBase ORM Microservice is a standalone Golang service that provides secure, project-scoped database access to CocoBase users. It exposes database operations through REST endpoints, allowing users to interact with their CocoBase project data from any programming language without needing direct database credentials.

### Key Principles
1. **Security First**: All operations are scoped to the user's project via API keys
2. **Language Agnostic**: REST API accessible from any language/platform
3. **Rich Query Capabilities**: Support complex queries, relationships, aggregations
4. **High Performance**: Built in Go for speed and concurrency
5. **Zero Trust**: Every request must be authenticated and authorized

---

## 🔐 Security Architecture

### Authentication Flow

```
Client Request → API Key Validation → Project Scope Validation → Operation Authorization → Database Query
```

### ORM API Key Structure

**Format:** `coco_orm_<project_id>_<random_32_chars>`

**Example:** `coco_orm_901235c6-9564-4de0-bb40_8a7f3e9d2c1b4f6a8e5d7c9b3a1f2e4d`

### Key Requirements
- **Generation**: Users generate ORM keys through main CocoBase API
- **Storage**: Keys stored hashed in database (bcrypt/argon2)
- **Permissions**: Each key has specific permissions (read, write, delete, admin)
- **Expiry**: Keys can have expiration dates
- **Revocation**: Users can revoke keys instantly
- **Rate Limiting**: Per-key rate limiting to prevent abuse
- **Audit Logging**: All operations logged with key ID and timestamp

### Security Layers

1. **Project Isolation**
   - Every query automatically filters by `project_id`
   - Users can ONLY access collections/documents in their project
   - No cross-project data leakage possible

2. **Permission Scoping**
   - Keys have granular permissions (read-only, write-only, full access)
   - Collection-level permissions enforced
   - Document-level permissions via AppUser roles

3. **Input Validation**
   - All inputs sanitized against SQL injection
   - JSON payloads validated
   - Field name whitelisting
   - Query complexity limits

4. **Rate Limiting**
   - Per-key rate limits based on pricing plan
   - Burst protection
   - Exponential backoff on failures

---

## 📊 Current Database Structure

### Database: PostgreSQL (Supabase)

### Core Tables

#### 1. **projects**
```sql
id              STRING (UUID)    PRIMARY KEY
name            STRING           NOT NULL
user_id         STRING           FOREIGN KEY → users.id
api_key         STRING           UNIQUE (main CocoBase API key)
created_at      TIMESTAMP
allowed_origins ARRAY[STRING]
callback_url    STRING
configs         JSON
active          BOOLEAN          DEFAULT true
storage_used_bytes BIGINT        DEFAULT 0
storage_last_updated TIMESTAMP
```

**Relationships:**
- Belongs to User (owner)
- Has many Collections
- Has many ProjectSubscriptions
- Has many Payments

---

#### 2. **collections**
```sql
id              STRING (UUID)    PRIMARY KEY
name            STRING           NOT NULL
created_at      TIMESTAMP
project_id      STRING           FOREIGN KEY → projects.id (CASCADE DELETE)
webhook_url     STRING           NULL
permissions     JSONB            DEFAULT {"create":[],"read":[],"update":[],"delete":[]}
```

**Indexes:**
- `idx_collection_project_id_name` (name, project_id)

**Relationships:**
- Belongs to Project
- Has many Documents (cascade delete)

**Permissions Structure:**
```json
{
  "create": ["admin", "editor"],
  "read": ["admin", "editor", "viewer"],
  "update": ["admin", "editor"],
  "delete": ["admin"]
}
```

---

#### 3. **documents**
```sql
id              STRING (UUID)    PRIMARY KEY
collection_id   STRING           FOREIGN KEY → collections.id (CASCADE DELETE)
data            JSONB            NOT NULL (stores all document fields)
created_at      TIMESTAMP
```

**Indexes:**
- `ix_documents_data_gin` (GIN index on data JSONB)
- `ix_documents_created_at` (created_at)
- `ix_documents_collection_created` (collection_id, created_at)

**Relationships:**
- Belongs to Collection

**Data Structure Example:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "age": 30,
  "status": "active",
  "tags": ["developer", "golang"],
  "author_id": "user-uuid-here",
  "metadata": {
    "lastLogin": "2025-01-15T10:30:00Z"
  }
}
```

---

#### 4. **app_users** (End Users of Client Projects)
```sql
id              STRING (UUID)    PRIMARY KEY
client_id       STRING           FOREIGN KEY → projects.id
email           STRING           NOT NULL
password        STRING           NOT NULL (hashed)
data            JSONB            NULL (custom user fields)
created_at      TIMESTAMP
oauth_id        STRING           UNIQUE NULL
oauth_provider  STRING           NULL
roles           ARRAY[STRING]    DEFAULT []
```

**Indexes:**
- `uq_client_email` UNIQUE (client_id, email)
- `ix_app_users_created_at` (created_at)
- `ix_app_users_oauth_id` (oauth_id)
- `ix_app_users_data_gin` (GIN index on data)

**Relationships:**
- Belongs to Project (client_id)

---

#### 5. **users** (CocoBase Platform Users)
```sql
id              STRING (UUID)    PRIMARY KEY
username        STRING
email           STRING           UNIQUE
password        STRING
full_name       STRING
created_at      TIMESTAMP
google_id       STRING           UNIQUE NULL
confirmed_email BOOLEAN          DEFAULT false
is_staff        BOOLEAN          DEFAULT false
```

**Relationships:**
- Has many Projects (owner)
- Has many Shared Projects (via project_shares)

---

#### 6. **pricing_plans**
```sql
id                      INTEGER      PRIMARY KEY
name                    STRING       UNIQUE
description             STRING
price                   FLOAT
currency                STRING       DEFAULT 'USD'
duration_days           INTEGER      DEFAULT 30
max_requests_per_month  INTEGER
max_storage_mb          INTEGER
max_users               INTEGER
max_cloud_functions     INTEGER
features                JSON
is_active               BOOLEAN      DEFAULT true
is_free                 BOOLEAN      DEFAULT false
created_at              TIMESTAMP
updated_at              TIMESTAMP
```

---

#### 7. **project_subscriptions**
```sql
id                  INTEGER     PRIMARY KEY
project_id          STRING      FOREIGN KEY → projects.id
plan_id             INTEGER     FOREIGN KEY → pricing_plans.id
start_date          TIMESTAMP
end_date            TIMESTAMP   NULL
is_active           BOOLEAN     DEFAULT true
auto_renew          BOOLEAN     DEFAULT true
grace_period_days   INTEGER     DEFAULT 3
```

---

#### 8. **orm_api_keys** (NEW - To Be Created)
```sql
id              STRING (UUID)    PRIMARY KEY
project_id      STRING           FOREIGN KEY → projects.id (CASCADE DELETE)
key_hash        STRING           NOT NULL (bcrypt hash of key)
key_prefix      STRING           NOT NULL (first 16 chars for identification)
name            STRING           NOT NULL (user-defined name)
permissions     JSON             NOT NULL
created_at      TIMESTAMP
last_used_at    TIMESTAMP        NULL
expires_at      TIMESTAMP        NULL
is_active       BOOLEAN          DEFAULT true
created_by      STRING           FOREIGN KEY → users.id
rate_limit      INTEGER          NULL (requests per minute, null = plan default)
```

**Indexes:**
- `idx_orm_keys_project` (project_id)
- `idx_orm_keys_prefix` (key_prefix)
- `idx_orm_keys_active` (is_active, project_id)

**Permissions Structure:**
```json
{
  "collections": {
    "*": ["read"],
    "users": ["read", "write"],
    "orders": ["read", "write", "delete"]
  },
  "admin": false,
  "auth": {
    "manage_users": true,
    "manage_roles": false
  }
}
```

---

#### 9. **project_auth_config** (NEW - To Be Created)
```sql
id                      STRING (UUID)    PRIMARY KEY
project_id              STRING           UNIQUE FOREIGN KEY → projects.id (CASCADE DELETE)
jwt_secret_hash         STRING           NULL (encrypted JWT secret)
jwt_algorithm           STRING           DEFAULT 'HS256'
public_key              TEXT             NULL (for asymmetric algorithms)
private_key_hash        TEXT             NULL (encrypted, for asymmetric algorithms)
access_token_expiry     INTEGER          DEFAULT 3600 (seconds)
refresh_token_expiry    INTEGER          DEFAULT 2592000 (30 days)
password_min_length     INTEGER          DEFAULT 8
password_regex          STRING           NULL
require_email_verification BOOLEAN       DEFAULT false
allow_registration      BOOLEAN          DEFAULT true
allow_oauth             BOOLEAN          DEFAULT true
created_at              TIMESTAMP
updated_at              TIMESTAMP
```

**Indexes:**
- `idx_auth_config_project` (project_id)

---

#### 10. **oauth_providers** (NEW - To Be Created)
```sql
id              STRING (UUID)    PRIMARY KEY
project_id      STRING           FOREIGN KEY → projects.id (CASCADE DELETE)
provider        STRING           NOT NULL (google, github, apple, etc.)
client_id       STRING           NOT NULL
client_secret   STRING           NOT NULL (encrypted)
redirect_uri    STRING           NOT NULL
enabled         BOOLEAN          DEFAULT true
scopes          ARRAY[STRING]    DEFAULT []
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

**Indexes:**
- `idx_oauth_project_provider` UNIQUE (project_id, provider)

---

#### 11. **refresh_tokens** (NEW - To Be Created)
```sql
id              STRING (UUID)    PRIMARY KEY
user_id         STRING           FOREIGN KEY → app_users.id (CASCADE DELETE)
project_id      STRING           FOREIGN KEY → projects.id (CASCADE DELETE)
token_hash      STRING           NOT NULL (hashed refresh token)
device_info     JSONB            NULL (browser, OS, device name)
ip_address      STRING           NULL
expires_at      TIMESTAMP        NOT NULL
revoked         BOOLEAN          DEFAULT false
revoked_at      TIMESTAMP        NULL
created_at      TIMESTAMP
last_used_at    TIMESTAMP        NULL
```

**Indexes:**
- `idx_refresh_tokens_user` (user_id, revoked)
- `idx_refresh_tokens_hash` (token_hash)
- `idx_refresh_tokens_expires` (expires_at)

**Device Info Structure:**
```json
{
  "browser": "Chrome",
  "os": "Windows 10",
  "device": "Desktop",
  "user_agent": "Mozilla/5.0..."
}
```

---

#### 12. **password_reset_tokens** (NEW - To Be Created)
```sql
id              STRING (UUID)    PRIMARY KEY
user_id         STRING           FOREIGN KEY → app_users.id (CASCADE DELETE)
project_id      STRING           FOREIGN KEY → projects.id (CASCADE DELETE)
token_hash      STRING           NOT NULL (hashed token)
expires_at      TIMESTAMP        NOT NULL
used            BOOLEAN          DEFAULT false
used_at         TIMESTAMP        NULL
ip_address      STRING           NULL
created_at      TIMESTAMP
```

**Indexes:**
- `idx_reset_tokens_user` (user_id, used)
- `idx_reset_tokens_hash` (token_hash)
- `idx_reset_tokens_expires` (expires_at)

---

#### 13. **email_verification_tokens** (NEW - To Be Created)
```sql
id              STRING (UUID)    PRIMARY KEY
user_id         STRING           FOREIGN KEY → app_users.id (CASCADE DELETE)
project_id      STRING           FOREIGN KEY → projects.id (CASCADE DELETE)
token_hash      STRING           NOT NULL (hashed token)
email           STRING           NOT NULL (email to verify)
expires_at      TIMESTAMP        NOT NULL
verified        BOOLEAN          DEFAULT false
verified_at     TIMESTAMP        NULL
created_at      TIMESTAMP
```

**Indexes:**
- `idx_verify_tokens_user` (user_id, verified)
- `idx_verify_tokens_hash` (token_hash)
- `idx_verify_tokens_expires` (expires_at)

---

#### 14. **user_sessions** (NEW - To Be Created)
```sql
id              STRING (UUID)    PRIMARY KEY
user_id         STRING           FOREIGN KEY → app_users.id (CASCADE DELETE)
project_id      STRING           FOREIGN KEY → projects.id (CASCADE DELETE)
session_token   STRING           NOT NULL (hashed)
device_info     JSONB            NULL
ip_address      STRING           NULL
expires_at      TIMESTAMP        NOT NULL
revoked         BOOLEAN          DEFAULT false
revoked_at      TIMESTAMP        NULL
created_at      TIMESTAMP
last_active_at  TIMESTAMP
```

**Indexes:**
- `idx_sessions_user` (user_id, revoked)
- `idx_sessions_token` (session_token)
- `idx_sessions_expires` (expires_at)

---

#### 15. **webhook_configs** (NEW - To Be Created)
```sql
id              STRING (UUID)    PRIMARY KEY
project_id      STRING           FOREIGN KEY → projects.id (CASCADE DELETE)
event           STRING           NOT NULL (user.registered, password.reset_requested, etc.)
url             STRING           NOT NULL
secret          STRING           NULL (for signing webhook payloads)
enabled         BOOLEAN          DEFAULT true
retry_enabled   BOOLEAN          DEFAULT true
max_retries     INTEGER          DEFAULT 3
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

**Indexes:**
- `idx_webhooks_project_event` (project_id, event, enabled)

**Supported Events:**
- `user.registered`
- `user.login`
- `user.logout`
- `user.updated`
- `user.deleted`
- `password.reset_requested`
- `password.changed`
- `email.verification_requested`
- `email.verified`
- `session.created`
- `session.revoked`
- `role.assigned`
- `role.removed`

---

#### 16. **webhook_logs** (NEW - To Be Created)
```sql
id              STRING (UUID)    PRIMARY KEY
webhook_id      STRING           FOREIGN KEY → webhook_configs.id (CASCADE DELETE)
project_id      STRING           FOREIGN KEY → projects.id (CASCADE DELETE)
event           STRING           NOT NULL
url             STRING           NOT NULL
payload         JSONB            NOT NULL
response_code   INTEGER          NULL
response_body   TEXT             NULL
success         BOOLEAN          NOT NULL
attempt         INTEGER          DEFAULT 1
error           TEXT             NULL
created_at      TIMESTAMP
```

**Indexes:**
- `idx_webhook_logs_webhook` (webhook_id, created_at)
- `idx_webhook_logs_project` (project_id, created_at)
- `idx_webhook_logs_success` (success, created_at)

---

#### 17. **email_configs** (NEW - To Be Created)
```sql
id              STRING (UUID)    PRIMARY KEY
project_id      STRING           UNIQUE FOREIGN KEY → projects.id (CASCADE DELETE)
provider        STRING           NOT NULL (sendgrid, mailgun, ses, etc.)
api_key         STRING           NOT NULL (encrypted)
from_email      STRING           NOT NULL
from_name       STRING           NOT NULL
smtp_host       STRING           NULL
smtp_port       INTEGER          NULL
smtp_username   STRING           NULL
smtp_password   STRING           NULL (encrypted)
enabled         BOOLEAN          DEFAULT true
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

**Indexes:**
- `idx_email_configs_project` (project_id)

---

#### 18. **email_templates** (NEW - To Be Created)
```sql
id              STRING (UUID)    PRIMARY KEY
project_id      STRING           FOREIGN KEY → projects.id (CASCADE DELETE)
template_name   STRING           NOT NULL (welcome_email, password_reset, etc.)
subject         STRING           NOT NULL
html_body       TEXT             NOT NULL
text_body       TEXT             NULL
variables       JSONB            NULL (list of available variables)
created_at      TIMESTAMP
updated_at      TIMESTAMP
```

**Indexes:**
- `idx_email_templates_project_name` UNIQUE (project_id, template_name)

**Standard Template Names:**
- `welcome_email`
- `password_reset`
- `email_verification`
- `password_changed`
- `account_deleted`
- `role_changed`

---

#### 19. **user_api_keys** (NEW - To Be Created)
```sql
id              STRING (UUID)    PRIMARY KEY
user_id         STRING           FOREIGN KEY → app_users.id (CASCADE DELETE)
project_id      STRING           FOREIGN KEY → projects.id (CASCADE DELETE)
key_hash        STRING           NOT NULL (bcrypt hash)
key_prefix      STRING           NOT NULL
name            STRING           NOT NULL
permissions     ARRAY[STRING]    DEFAULT []
created_at      TIMESTAMP
last_used_at    TIMESTAMP        NULL
expires_at      TIMESTAMP        NULL
revoked         BOOLEAN          DEFAULT false
revoked_at      TIMESTAMP        NULL
```

**Indexes:**
- `idx_user_api_keys_user` (user_id, revoked)
- `idx_user_api_keys_hash` (key_hash)
- `idx_user_api_keys_prefix` (key_prefix)

**Permissions Examples:**
```json
["read:posts", "write:comments", "delete:own_comments", "read:users"]
```

---

#### 20. **totp_secrets** (NEW - To Be Created)
```sql
id              STRING (UUID)    PRIMARY KEY
user_id         STRING           UNIQUE FOREIGN KEY → app_users.id (CASCADE DELETE)
project_id      STRING           FOREIGN KEY → projects.id (CASCADE DELETE)
secret          STRING           NOT NULL (encrypted TOTP secret)
backup_codes    JSONB            NOT NULL (array of hashed backup codes)
enabled         BOOLEAN          DEFAULT false
verified        BOOLEAN          DEFAULT false
created_at      TIMESTAMP
enabled_at      TIMESTAMP        NULL
```

**Indexes:**
- `idx_totp_user` (user_id)
- `idx_totp_enabled` (enabled, project_id)

**Backup Codes Structure:**
```json
{
  "codes": [
    {"code_hash": "hash1", "used": false, "used_at": null},
    {"code_hash": "hash2", "used": false, "used_at": null}
  ]
}
```

---

#### 21. **audit_logs** (NEW - To Be Created)
```sql
id              STRING (UUID)    PRIMARY KEY
project_id      STRING           FOREIGN KEY → projects.id (CASCADE DELETE)
user_id         STRING           NULL FOREIGN KEY → app_users.id
orm_key_id      STRING           NULL FOREIGN KEY → orm_api_keys.id
action          STRING           NOT NULL (login, logout, create_document, etc.)
resource_type   STRING           NULL (collection, document, user, etc.)
resource_id     STRING           NULL
metadata        JSONB            NULL (additional context)
ip_address      STRING           NULL
user_agent      STRING           NULL
success         BOOLEAN          NOT NULL
error_message   TEXT             NULL
created_at      TIMESTAMP
```

**Indexes:**
- `idx_audit_logs_project_created` (project_id, created_at)
- `idx_audit_logs_user_created` (user_id, created_at)
- `idx_audit_logs_action` (action, created_at)
- `idx_audit_logs_resource` (resource_type, resource_id, created_at)

**Common Actions:**
- `auth.login`
- `auth.logout`
- `auth.register`
- `auth.password_change`
- `auth.password_reset`
- `document.create`
- `document.read`
- `document.update`
- `document.delete`
- `collection.create`
- `collection.update`
- `collection.delete`
- `role.assign`
- `role.remove`

---

#### Updates to Existing Tables

##### **app_users** (ADD COLUMNS)
```sql
-- Add these columns to existing table
email_verified      BOOLEAN          DEFAULT false
email_verified_at   TIMESTAMP        NULL
suspended           BOOLEAN          DEFAULT false
suspended_at        TIMESTAMP        NULL
suspended_reason    TEXT             NULL
suspended_until     TIMESTAMP        NULL
last_login_at       TIMESTAMP        NULL
last_login_ip       STRING           NULL
failed_login_attempts INTEGER        DEFAULT 0
locked_until        TIMESTAMP        NULL
```

**New Indexes:**
- `idx_app_users_suspended` (suspended, client_id)
- `idx_app_users_email_verified` (email_verified, client_id)

---

## 🚀 Core Features

### 1. **Authentication & Authorization Management**

The ORM provides complete authentication and authorization capabilities, allowing developers to build full backends without additional services.

#### 1.1 **User Authentication (AppUser Management)**

##### Register User
```http
POST /v1/auth/register
Authorization: Bearer coco_orm_...

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "data": {
    "name": "John Doe",
    "phone": "+1234567890"
  },
  "roles": ["user"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "user-uuid",
      "email": "user@example.com",
      "roles": ["user"],
      "created_at": "2025-01-15T10:30:00Z"
    },
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 3600
  }
}
```

---

##### Login User
```http
POST /v1/auth/login
Authorization: Bearer coco_orm_...

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "user-uuid",
      "email": "user@example.com",
      "roles": ["user", "admin"],
      "data": {
        "name": "John Doe"
      }
    },
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 3600
  }
}
```

---

##### OAuth Login (Google, GitHub, Apple)
```http
POST /v1/auth/oauth/{provider}
Authorization: Bearer coco_orm_...

{
  "oauth_token": "google-oauth-token",
  "oauth_id": "google-user-id-123",
  "email": "user@example.com",
  "name": "John Doe"
}
```

**Supported Providers:** `google`, `github`, `apple`, `facebook`, `twitter`

---

##### Refresh Token
```http
POST /v1/auth/refresh
Authorization: Bearer coco_orm_...

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

---

##### Logout
```http
POST /v1/auth/logout
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..." // Optional: invalidate specific token
}
```

---

##### Get Current User
```http
GET /v1/auth/me
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "user-uuid",
    "email": "user@example.com",
    "roles": ["user", "admin"],
    "data": {
      "name": "John Doe",
      "phone": "+1234567890"
    },
    "created_at": "2025-01-15T10:30:00Z"
  }
}
```

---

##### Update User Profile
```http
PATCH /v1/auth/me
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...

{
  "data": {
    "name": "John Smith",
    "avatar": "https://example.com/avatar.jpg"
  }
}
```

---

##### Change Password
```http
POST /v1/auth/change-password
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...

{
  "current_password": "OldPass123!",
  "new_password": "NewSecurePass456!"
}
```

---

##### Request Password Reset
```http
POST /v1/auth/forgot-password
Authorization: Bearer coco_orm_...

{
  "email": "user@example.com"
}
```

**Note:** This sends a reset token to the project's callback URL for the project owner to handle email delivery.

---

##### Reset Password
```http
POST /v1/auth/reset-password
Authorization: Bearer coco_orm_...

{
  "token": "reset-token-from-email",
  "new_password": "NewSecurePass456!"
}
```

---

#### 1.2 **JWT Token Management**

##### JWT Token Structure
```json
{
  "sub": "user-uuid",
  "email": "user@example.com",
  "project_id": "project-uuid",
  "roles": ["user", "admin"],
  "iat": 1705315800,
  "exp": 1705319400,
  "token_type": "access"
}
```

##### Validate JWT Token
```http
POST /v1/auth/validate
Authorization: Bearer coco_orm_...

{
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "user_id": "user-uuid",
    "email": "user@example.com",
    "roles": ["user", "admin"],
    "expires_at": "2025-01-15T11:30:00Z"
  }
}
```

---

##### Decode JWT Token (without validation)
```http
POST /v1/auth/decode
Authorization: Bearer coco_orm_...

{
  "token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Use Case:** Inspect token payload without verifying signature (e.g., for debugging)

---

#### 1.3 **Role-Based Access Control (RBAC)**

##### Assign Roles to User
```http
POST /v1/auth/users/{user_id}/roles
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs... (admin token)

{
  "roles": ["editor", "moderator"]
}
```

**Permission Required:** Admin role or specific `manage_roles` permission

---

##### Remove Roles from User
```http
DELETE /v1/auth/users/{user_id}/roles
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs... (admin token)

{
  "roles": ["moderator"]
}
```

---

##### List Users with Role
```http
GET /v1/auth/users?role=admin&limit=50
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs... (admin token)
```

---

##### Check User Permissions
```http
POST /v1/auth/check-permission
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...

{
  "collection": "posts",
  "action": "delete"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "allowed": true,
    "reason": "User has 'admin' role which grants 'delete' permission on 'posts' collection"
  }
}
```

---

#### 1.4 **Collection-Level Permissions**

##### Get Collection Permissions
```http
GET /v1/collections/{collection}/permissions
Authorization: Bearer coco_orm_...
```

**Response:**
```json
{
  "success": true,
  "data": {
    "create": ["admin", "editor"],
    "read": ["admin", "editor", "viewer", "user"],
    "update": ["admin", "editor"],
    "delete": ["admin"]
  }
}
```

---

##### Update Collection Permissions
```http
PATCH /v1/collections/{collection}/permissions
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs... (admin token)

{
  "permissions": {
    "create": ["admin", "editor", "contributor"],
    "read": ["*"],
    "update": ["admin", "editor"],
    "delete": ["admin"]
  }
}
```

**Special Values:**
- `["*"]` - Allow everyone (including unauthenticated users)
- `[]` - Allow no one (except project owner)
- `["user"]` - Require authentication (any logged-in user)

---

#### 1.5 **Session Management**

##### List Active Sessions
```http
GET /v1/auth/sessions
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "session_id": "session-uuid",
      "device": "Chrome on Windows",
      "ip_address": "192.168.1.100",
      "last_active": "2025-01-15T10:30:00Z",
      "created_at": "2025-01-14T08:00:00Z",
      "current": true
    },
    {
      "session_id": "session-uuid-2",
      "device": "Safari on iPhone",
      "ip_address": "192.168.1.101",
      "last_active": "2025-01-15T09:00:00Z",
      "created_at": "2025-01-13T12:00:00Z",
      "current": false
    }
  ]
}
```

---

##### Revoke Session
```http
DELETE /v1/auth/sessions/{session_id}
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...
```

---

##### Revoke All Sessions (except current)
```http
DELETE /v1/auth/sessions
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...
```

---

#### 1.6 **User Management (Admin Operations)**

##### List All Users
```http
GET /v1/auth/users?limit=50&offset=0&role=admin
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs... (admin token)
```

---

##### Get User by ID
```http
GET /v1/auth/users/{user_id}
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs... (admin token)
```

---

##### Update User (Admin)
```http
PATCH /v1/auth/users/{user_id}
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs... (admin token)

{
  "email": "newemail@example.com",
  "roles": ["admin", "editor"],
  "data": {
    "verified": true
  }
}
```

---

##### Delete User
```http
DELETE /v1/auth/users/{user_id}
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJHUzI1NiIs... (admin token)
```

---

##### Ban/Suspend User
```http
POST /v1/auth/users/{user_id}/suspend
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs... (admin token)

{
  "reason": "Violating community guidelines",
  "duration_days": 7
}
```

---

##### Unban User
```http
POST /v1/auth/users/{user_id}/unsuspend
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs... (admin token)
```

---

#### 1.7 **API Key Management for End Users**

Users can generate their own API keys (different from ORM keys) for machine-to-machine communication.

##### Create User API Key
```http
POST /v1/auth/api-keys
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...

{
  "name": "Mobile App Key",
  "permissions": ["read:posts", "write:comments"],
  "expires_in_days": 90
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "key-uuid",
    "key": "coco_user_abc123def456...",
    "name": "Mobile App Key",
    "permissions": ["read:posts", "write:comments"],
    "created_at": "2025-01-15T10:30:00Z",
    "expires_at": "2025-04-15T10:30:00Z"
  }
}
```

**Warning:** Key is only shown once during creation

---

##### List User API Keys
```http
GET /v1/auth/api-keys
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...
```

---

##### Revoke User API Key
```http
DELETE /v1/auth/api-keys/{key_id}
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...
```

---

#### 1.8 **Two-Factor Authentication (2FA)**

##### Enable 2FA
```http
POST /v1/auth/2fa/enable
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...
```

**Response:**
```json
{
  "success": true,
  "data": {
    "secret": "JBSWY3DPEHPK3PXP",
    "qr_code": "data:image/png;base64,iVBORw0KGgo...",
    "backup_codes": [
      "12345678",
      "23456789",
      "34567890"
    ]
  }
}
```

---

##### Verify 2FA Setup
```http
POST /v1/auth/2fa/verify
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...

{
  "code": "123456"
}
```

---

##### Disable 2FA
```http
POST /v1/auth/2fa/disable
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...

{
  "password": "CurrentPassword123!",
  "code": "123456"
}
```

---

#### 1.9 **Project Configuration & JWT Management**

Developers can configure authentication behavior and manage JWT secrets for their project.

##### Get Project Auth Configuration
```http
GET /v1/config/auth
Authorization: Bearer coco_orm_...
```

**Response:**
```json
{
  "success": true,
  "data": {
    "jwt_secret_exists": true,
    "jwt_algorithm": "HS256",
    "access_token_expiry": 3600,
    "refresh_token_expiry": 2592000,
    "password_min_length": 8,
    "require_email_verification": false,
    "allow_registration": true,
    "oauth_providers": {
      "google": true,
      "github": false,
      "apple": false
    },
    "webhook_urls": {
      "user_registered": "https://myapp.com/webhooks/user-registered",
      "user_login": null,
      "password_reset": "https://myapp.com/webhooks/password-reset"
    }
  }
}
```

---

##### Generate/Rotate JWT Secret
```http
POST /v1/config/auth/jwt-secret/generate
Authorization: Bearer coco_orm_...

{
  "algorithm": "HS256",
  "rotate": false
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "secret": "your-generated-secret-key-here",
    "algorithm": "HS256",
    "created_at": "2025-01-15T10:30:00Z"
  },
  "warning": "Store this secret securely. It will not be shown again. Use this to sign/verify JWTs in your custom authentication flows."
}
```

**Parameters:**
- `algorithm`: `HS256`, `HS384`, `HS512` (symmetric) or `RS256`, `RS384`, `RS512` (asymmetric)
- `rotate`: `true` to invalidate all existing tokens, `false` to keep them valid

**Use Cases:**
1. **Custom Authentication**: Sign your own JWTs for custom login flows
2. **Microservice Integration**: Share secret with other services for token validation
3. **Security Rotation**: Periodically rotate secrets for security

---

##### Set Custom JWT Secret
```http
POST /v1/config/auth/jwt-secret/set
Authorization: Bearer coco_orm_...

{
  "secret": "your-custom-secret-at-least-32-chars-long",
  "algorithm": "HS256"
}
```

**Use Case:** Use your existing JWT infrastructure/secret

---

##### Get Public Key (for RS256/RS384/RS512)
```http
GET /v1/config/auth/jwt-secret/public-key
Authorization: Bearer coco_orm_...
```

**Response:**
```json
{
  "success": true,
  "data": {
    "public_key": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBg...",
    "algorithm": "RS256",
    "key_id": "key-20250115"
  }
}
```

**Use Case:** Share public key with other services for JWT verification without exposing private key

---

##### Update Auth Configuration
```http
PATCH /v1/config/auth
Authorization: Bearer coco_orm_...

{
  "access_token_expiry": 7200,
  "refresh_token_expiry": 604800,
  "password_min_length": 10,
  "require_email_verification": true,
  "allow_registration": true,
  "password_regex": "^(?=.*[A-Z])(?=.*[a-z])(?=.*\\d).{10,}$"
}
```

---

##### Configure OAuth Providers
```http
POST /v1/config/auth/oauth
Authorization: Bearer coco_orm_...

{
  "provider": "google",
  "client_id": "your-google-client-id",
  "client_secret": "your-google-client-secret",
  "redirect_uri": "https://myapp.com/auth/google/callback",
  "enabled": true
}
```

**Supported Providers:** `google`, `github`, `apple`, `facebook`, `twitter`, `microsoft`

---

#### 1.10 **Webhook Configuration**

Configure webhooks to receive notifications about authentication events.

##### Set Webhook URL for Auth Events
```http
POST /v1/config/webhooks
Authorization: Bearer coco_orm_...

{
  "events": {
    "user.registered": "https://myapp.com/webhooks/user-registered",
    "user.login": "https://myapp.com/webhooks/user-login",
    "user.logout": null,
    "user.updated": "https://myapp.com/webhooks/user-updated",
    "user.deleted": "https://myapp.com/webhooks/user-deleted",
    "password.reset_requested": "https://myapp.com/webhooks/password-reset",
    "password.changed": "https://myapp.com/webhooks/password-changed",
    "session.created": null,
    "session.revoked": null
  },
  "secret": "webhook-signing-secret"
}
```

**Webhook Payload Example (user.registered):**
```json
{
  "event": "user.registered",
  "timestamp": "2025-01-15T10:30:00Z",
  "project_id": "project-uuid",
  "data": {
    "user_id": "user-uuid",
    "email": "newuser@example.com",
    "roles": ["user"],
    "created_at": "2025-01-15T10:30:00Z"
  },
  "signature": "sha256=abc123..."
}
```

**Webhook Payload Example (password.reset_requested):**
```json
{
  "event": "password.reset_requested",
  "timestamp": "2025-01-15T10:30:00Z",
  "project_id": "project-uuid",
  "data": {
    "user_id": "user-uuid",
    "email": "user@example.com",
    "reset_token": "secure-reset-token-here",
    "reset_url": "https://myapp.com/reset-password?token=secure-reset-token-here",
    "expires_at": "2025-01-15T11:30:00Z"
  },
  "signature": "sha256=abc123..."
}
```

**Use Cases:**
1. **Email Notifications**: Send welcome emails on registration
2. **Slack Alerts**: Notify team on new user signups
3. **Custom Password Reset Emails**: Handle reset flow yourself
4. **Audit Logging**: Log auth events to external systems
5. **Analytics**: Track user behavior in your analytics platform

---

##### Test Webhook
```http
POST /v1/config/webhooks/test
Authorization: Bearer coco_orm_...

{
  "event": "user.registered",
  "url": "https://myapp.com/webhooks/test"
}
```

---

#### 1.11 **Email Template Management (Optional)**

If you want CocoBase ORM to handle email sending (instead of webhooks), configure templates.

##### Set Email Provider Configuration
```http
POST /v1/config/email
Authorization: Bearer coco_orm_...

{
  "provider": "sendgrid",
  "api_key": "your-sendgrid-api-key",
  "from_email": "noreply@myapp.com",
  "from_name": "MyApp"
}
```

**Supported Providers:** `sendgrid`, `mailgun`, `ses`, `smtp`, `postmark`, `resend`

---

##### Configure Email Templates
```http
POST /v1/config/email/templates
Authorization: Bearer coco_orm_...

{
  "welcome_email": {
    "subject": "Welcome to {{app_name}}!",
    "html": "<h1>Welcome {{user_name}}!</h1><p>Thanks for joining.</p>",
    "text": "Welcome {{user_name}}! Thanks for joining."
  },
  "password_reset": {
    "subject": "Reset your password",
    "html": "<p>Click here: <a href='{{reset_url}}'>Reset Password</a></p>",
    "text": "Reset your password: {{reset_url}}"
  },
  "email_verification": {
    "subject": "Verify your email",
    "html": "<p>Click here: <a href='{{verify_url}}'>Verify Email</a></p>",
    "text": "Verify your email: {{verify_url}}"
  }
}
```

**Template Variables:**
- `{{app_name}}` - Project name
- `{{user_name}}` - User's name
- `{{user_email}}` - User's email
- `{{reset_url}}` - Password reset URL
- `{{verify_url}}` - Email verification URL
- `{{reset_token}}` - Raw reset token
- `{{verify_token}}` - Raw verification token

---

#### 1.12 **Custom Authentication Flows**

For advanced use cases, developers can implement custom authentication logic while still using CocoBase ORM for storage.

##### Create User (without auto-login)
```http
POST /v1/auth/users/create
Authorization: Bearer coco_orm_...

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "data": {
    "name": "John Doe",
    "source": "mobile_app"
  },
  "roles": ["user"],
  "skip_password_hash": false,
  "send_welcome_email": false
}
```

**Use Case:** Batch user creation, migration from another platform

---

##### Verify Email
```http
POST /v1/auth/verify-email
Authorization: Bearer coco_orm_...

{
  "token": "email-verification-token"
}
```

---

##### Custom Token Generation
```http
POST /v1/auth/token/generate
Authorization: Bearer coco_orm_...

{
  "user_id": "user-uuid",
  "expires_in": 3600,
  "custom_claims": {
    "subscription": "premium",
    "features": ["feature_a", "feature_b"]
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 3600,
    "token_type": "Bearer"
  }
}
```

**Use Case:** Sign tokens with custom claims after your own verification logic

---

##### Verify Password (without login)
```http
POST /v1/auth/verify-password
Authorization: Bearer coco_orm_...

{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "user_id": "user-uuid"
  }
}
```

**Use Case:** Re-authentication before sensitive operations

---

### 2. **CRUD Operations**

#### Create Document
```http
POST /v1/collections/{collection}/documents
Authorization: Bearer coco_orm_...

{
  "data": {
    "name": "Product A",
    "price": 99.99,
    "stock": 50
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "doc-uuid",
    "created_at": "2025-01-15T10:30:00Z",
    "name": "Product A",
    "price": 99.99,
    "stock": 50
  }
}
```

---

#### Read Documents (with filtering)
```http
GET /v1/collections/{collection}/documents?status=active&age_gte=18&limit=50&offset=0
Authorization: Bearer coco_orm_...
```

**Query Parameters:**
- Basic filters: `field=value`
- Comparison operators: `field_gte`, `field_lt`, `field_contains`, etc.
- Logical operators: `[or]field=value`
- Sorting: `sort=created_at&order=desc`
- Pagination: `limit=50&offset=0`

---

#### Update Document
```http
PATCH /v1/collections/{collection}/documents/{doc_id}
Authorization: Bearer coco_orm_...

{
  "data": {
    "status": "completed"
  }
}
```

**Array Operations:**
```http
PATCH /v1/collections/{collection}/documents/{doc_id}

{
  "data": {
    "status": "active"
  },
  "$append": {
    "tags": ["featured", "sale"]
  },
  "$remove": {
    "tags": ["draft"]
  }
}
```

---

#### Delete Document
```http
DELETE /v1/collections/{collection}/documents/{doc_id}
Authorization: Bearer coco_orm_...
```

---

### 2. **Advanced Query Operations**

#### Complex Filtering with Boolean Logic
```http
GET /v1/collections/users/documents?status=active&[or]age_gte=18&[or]role=admin
```

**Translates to:** `status = 'active' AND (age >= 18 OR role = 'admin')`

#### OR Groups
```http
GET /v1/collections/posts/documents?[or:a]status=published&[or:a]featured=true&[or:b]author_id=123&[or:b]editor_id=456
```

**Translates to:** `(status = 'published' OR featured = true) AND (author_id = 123 OR editor_id = 456)`

---

### 3. **Relationship Population**

#### Auto-populate Related Documents
```http
GET /v1/collections/posts/documents?populate=author&populate=category
```

**Response:**
```json
{
  "data": [
    {
      "id": "post-1",
      "title": "Hello World",
      "author_id": "user-123",
      "author": {
        "id": "user-123",
        "name": "John Doe",
        "email": "john@example.com"
      },
      "category_id": "cat-1",
      "category": {
        "id": "cat-1",
        "name": "Technology"
      }
    }
  ]
}
```

#### Nested Population
```http
GET /v1/collections/comments/documents?populate=post.author
```

---

### 4. **Aggregation Operations**

#### Count Documents
```http
GET /v1/collections/{collection}/count?status=active
```

**Response:**
```json
{
  "count": 342
}
```

---

#### Aggregate Functions
```http
GET /v1/collections/orders/aggregate?field=total&operation=sum&status=completed
```

**Operations:** `count`, `sum`, `avg`, `min`, `max`

**Response:**
```json
{
  "field": "total",
  "operation": "sum",
  "result": 45280.50,
  "collection": "orders"
}
```

---

#### Group By
```http
GET /v1/collections/users/documents/group-by?field=country
```

**Response:**
```json
{
  "data": [
    {"country": "US", "count": 150},
    {"country": "UK", "count": 80},
    {"country": "CA", "count": 45}
  ]
}
```

---

### 5. **Batch Operations**

#### Batch Create
```http
POST /v1/collections/{collection}/batch/create
Authorization: Bearer coco_orm_...

{
  "documents": [
    {"name": "John", "age": 25},
    {"name": "Jane", "age": 30},
    {"name": "Bob", "age": 35}
  ]
}
```

**Response:**
```json
{
  "success": true,
  "created": 3,
  "data": [...]
}
```

---

#### Batch Update
```http
POST /v1/collections/{collection}/batch/update
Authorization: Bearer coco_orm_...

{
  "updates": {
    "doc-1": {"data": {"status": "completed"}},
    "doc-2": {"data": {"status": "pending"}}
  }
}
```

---

#### Batch Delete
```http
POST /v1/collections/{collection}/batch/delete
Authorization: Bearer coco_orm_...

{
  "document_ids": ["doc-1", "doc-2", "doc-3"]
}
```

---

### 6. **Schema Introspection**

#### Get Collection Schema
```http
GET /v1/collections/{collection}/schema
Authorization: Bearer coco_orm_...
```

**Response:**
```json
{
  "collection": "users",
  "document_count": 1250,
  "analyzed_documents": 100,
  "fields": {
    "name": {
      "types": ["str"],
      "primary_type": "str",
      "nullable": false,
      "null_percentage": 0,
      "samples": ["John Doe", "Jane Smith"]
    },
    "age": {
      "types": ["int"],
      "primary_type": "int",
      "nullable": true,
      "null_percentage": 5.2,
      "samples": [25, 30, 42]
    },
    "author_id": {
      "types": ["str"],
      "primary_type": "str",
      "nullable": false,
      "null_percentage": 0,
      "samples": ["user-123", "user-456"]
    }
  },
  "detected_relationships": {
    "author_id": {
      "type": "belongs_to",
      "field": "author_id",
      "target_collection": "authors",
      "confidence": "high"
    }
  }
}
```

---

### 7. **Transaction Support**

#### Begin Transaction
```http
POST /v1/transactions/begin
Authorization: Bearer coco_orm_...

Response: {"transaction_id": "tx-uuid"}
```

---

#### Execute Operations in Transaction
```http
POST /v1/collections/users/documents
Authorization: Bearer coco_orm_...
X-Transaction-ID: tx-uuid

{...}
```

---

#### Commit Transaction
```http
POST /v1/transactions/{tx_id}/commit
Authorization: Bearer coco_orm_...
```

---

#### Rollback Transaction
```http
POST /v1/transactions/{tx_id}/rollback
Authorization: Bearer coco_orm_...
```

---

### 8. **Real-time Subscriptions (WebSocket)**

#### Subscribe to Collection Changes
```javascript
ws://orm.cocobase.com/v1/subscribe
Authorization: coco_orm_...

// Subscribe message
{
  "action": "subscribe",
  "collection": "orders",
  "filters": {"status": "pending"}
}

// Receive updates
{
  "event": "document.created",
  "collection": "orders",
  "data": {...}
}
```

**Events:**
- `document.created`
- `document.updated`
- `document.deleted`

---

### 9. **Export Operations**

#### Export Collection Data
```http
GET /v1/collections/{collection}/export?format=json&status=active
Authorization: Bearer coco_orm_...
```

**Formats:** `json`, `csv`, `ndjson`

---

### 10. **Search Operations**

#### Full-Text Search
```http
GET /v1/collections/{collection}/search?q=golang+developer&fields=title,description
Authorization: Bearer coco_orm_...
```

---

### 11. **File Upload & Storage Operations**

**Integration:** Uses existing CocoBase storage infrastructure (Backblaze B2 via S3-compatible API)

#### Current Storage Implementation

- **Provider:** Backblaze B2 (S3-compatible, using aioboto3)
- **Structure:** `projects/{project_id}/{subdirectory}/{filename}`
- **Public URL:** `https://f005.backblazeb2.com/file/{bucket}/projects/{project_id}/...`
- **Storage Tracking:** Cached in `projects.storage_used_bytes` column
- **Limits:** Based on pricing plan (`max_storage_mb` from pricing_plans table)
- **Async Upload:** Non-blocking async uploads using aioboto3

#### Upload File via ORM
```http
POST /v1/storage/files
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs... (optional - for user-scoped uploads)
Content-Type: multipart/form-data

file: [binary file data]
directory: "avatars" (optional - defaults to "media")
```

**Response:**
```json
{
  "success": true,
  "data": {
    "filename": "avatar_user123.jpg",
    "url": "https://f005.backblazeb2.com/file/cocobase/projects/project-uuid/avatars/avatar_user123.jpg",
    "size": 102400,
    "directory": "avatars",
    "uploaded_at": "2025-01-18T10:30:00Z"
  }
}
```

**Storage Path Structure:**
```
projects/
  {project_id}/
    media/              # Default directory
      file1.pdf
      file2.jpg
    avatars/            # Custom directory
      user_avatar.jpg
    documents/          # Another custom directory
      report.pdf
    {collection_name}/  # Collection-specific uploads
      doc_file.jpg
```

---

#### Get Project Files (List)
```http
GET /v1/storage/files?directory=avatars&limit=50
Authorization: Bearer coco_orm_...
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "filename": "avatar_user123.jpg",
      "url": "https://f005.backblazeb2.com/file/cocobase/projects/project-uuid/avatars/avatar_user123.jpg",
      "size": 102400,
      "last_modified": "2025-01-18T10:30:00Z",
      "etag": "abc123def456"
    }
  ]
}
```

---

#### Delete File
```http
DELETE /v1/storage/files/{filename}?directory=avatars
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs... (optional)
```

**Response:**
```json
{
  "success": true,
  "message": "File deleted successfully"
}
```

**Note:** Deleting a file also decrements the `storage_used_bytes` counter.

---

#### Get Storage Info
```http
GET /v1/storage/info
Authorization: Bearer coco_orm_...
```

**Response:**
```json
{
  "success": true,
  "data": {
    "total_storage": 524288000,
    "used": 45678900,
    "available": 478609100,
    "used_percentage": 8.7,
    "plan": "Pro Plan",
    "max_storage_mb": 500,
    "last_updated": "2025-01-18T10:30:00Z"
  }
}
```

---

#### Upload Files in Document Creation (Multipart Form)

Already implemented in collections endpoint:

```http
POST /v1/collections/users/documents
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...
Content-Type: multipart/form-data

data: {"name": "John Doe", "email": "john@example.com"}
avatar: [binary file]
resume: [binary file]
```

**How it works:**
1. Files uploaded to `projects/{project_id}/{collection_name}/`
2. File URLs automatically added to document data
3. Storage limits checked before upload
4. Storage cache updated after successful upload

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "doc-uuid",
    "name": "John Doe",
    "email": "john@example.com",
    "avatar": "https://f005.backblazeb2.com/file/cocobase/projects/project-uuid/users/avatar.jpg",
    "resume": "https://f005.backblazeb2.com/file/cocobase/projects/project-uuid/users/resume.pdf",
    "created_at": "2025-01-18T10:30:00Z"
  }
}
```

---

#### Upload Profile Picture (Auth Integration)
```http
PATCH /v1/auth/me
Authorization: Bearer coco_orm_...
X-User-Token: eyJhbGciOiJIUzI1NiIs...
Content-Type: multipart/form-data

data: {"name": "John Smith"}
avatar: [binary file]
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "user-uuid",
    "email": "user@example.com",
    "data": {
      "name": "John Smith",
      "avatar": "https://f005.backblazeb2.com/file/cocobase/projects/project-uuid/avatars/user-uuid.jpg"
    },
    "updated_at": "2025-01-18T10:30:00Z"
  }
}
```

---

#### Storage Limits & Enforcement

Storage limits enforced based on pricing plan:

| Plan | Max Storage |
|------|-------------|
| Free | 100 MB |
| Starter | 500 MB |
| Pro | 5 GB |
| Enterprise | Custom |

**Storage Exceeded Response (413):**
```json
{
  "success": false,
  "error": {
    "code": "STORAGE_LIMIT_EXCEEDED",
    "message": "Storage limit exceeded. Current: 450.5MB, Limit: 500MB",
    "details": {
      "current_usage_mb": 450.5,
      "limit_mb": 500,
      "available_mb": 49.5
    },
    "request_id": "req-uuid"
  }
}
```

**Note:** System also sends notification to project users when storage limit is reached.

---

#### Storage Implementation Details

**Existing Python Functions (to replicate in Go):**

1. **`handle_file_upload(file_content, project_id, filename, subdirectory, db)`**
   - Async upload to B2 using aioboto3
   - Updates `storage_used_bytes` in projects table
   - Returns public URL

2. **`check_storage_limit(project_id, file_size, db)`**
   - Checks cached storage usage
   - Compares with plan limit
   - Raises 413 error if exceeded
   - Sends notification to users

3. **`get_files(project_id, subdirectory)`**
   - Lists files in S3 bucket
   - Returns file metadata (size, last_modified, etag)

4. **`delete_s3_file(object_key)`**
   - Deletes file from S3
   - Should update storage cache (currently missing)

**Go Implementation Requirements:**
- Use `github.com/aws/aws-sdk-go-v2` for S3 operations
- Maintain async upload capability
- Cache storage usage in database
- Support concurrent uploads
- Implement file sanitization (spaces → underscores)

---

## 🔧 Technical Implementation Details

### Go Architecture

```
cocobase-orm/
├── cmd/
│   └── server/
│       └── main.go
├── internal/
│   ├── api/
│   │   ├── handlers/          # HTTP handlers
│   │   ├── middleware/        # Auth, logging, rate limiting
│   │   └── router/            # Route definitions
│   ├── auth/
│   │   ├── keystore.go        # API key management
│   │   └── validator.go       # Key validation
│   ├── database/
│   │   ├── connection.go      # DB connection pool
│   │   ├── queries.go         # SQL query builder
│   │   └── transactions.go    # Transaction handling
│   ├── models/
│   │   ├── project.go
│   │   ├── collection.go
│   │   ├── document.go
│   │   └── api_key.go
│   ├── query/
│   │   ├── builder.go         # Query DSL parser
│   │   ├── filter.go          # Filter compilation
│   │   └── relationships.go   # Relationship resolution
│   ├── security/
│   │   ├── sanitizer.go       # Input sanitization
│   │   ├── validator.go       # Input validation
│   │   └── ratelimit.go       # Rate limiting
│   └── cache/
│       └── redis.go           # Redis caching layer
├── pkg/
│   ├── errors/                # Error definitions
│   └── utils/                 # Utilities
├── configs/
│   └── config.yaml
└── tests/
```

---

### Key Dependencies

```go
// Database
"github.com/jackc/pgx/v5"           // PostgreSQL driver
"github.com/jackc/pgx/v5/pgxpool"   // Connection pooling

// Web Framework
"github.com/gofiber/fiber/v3"       // Fast HTTP framework
"github.com/gofiber/contrib/websocket" // WebSocket support

// Authentication
"golang.org/x/crypto/bcrypt"        // Password hashing

// Caching
"github.com/redis/go-redis/v9"      // Redis client

// Validation
"github.com/go-playground/validator/v10"

// JSON
"github.com/goccy/go-json"          // Fast JSON parser

// Rate Limiting
"golang.org/x/time/rate"

// Logging
"go.uber.org/zap"                   // Fast logging

// Configuration
"github.com/spf13/viper"
```

---

## 🛡️ Security Features

### 1. **SQL Injection Prevention**
- Parameterized queries ONLY
- No string concatenation for SQL
- Input validation on all fields

### 2. **Rate Limiting Strategy**
```
Free Plan:     100 requests/minute
Starter Plan:  500 requests/minute
Pro Plan:      2000 requests/minute
Enterprise:    Custom
```

### 3. **Request Validation**
- Max query complexity score
- Max JSON payload size: 10MB
- Max batch size: 1000 documents
- Field name whitelist pattern: `^[a-zA-Z0-9_.-]+$`

### 4. **Audit Logging**
```json
{
  "timestamp": "2025-01-15T10:30:00Z",
  "key_id": "key-uuid",
  "project_id": "proj-uuid",
  "method": "POST",
  "endpoint": "/v1/collections/users/documents",
  "ip_address": "192.168.1.100",
  "user_agent": "MyApp/1.0",
  "status_code": 201,
  "duration_ms": 45,
  "error": null
}
```

### 5. **DDoS Protection**
- Connection limits per IP
- Request size limits
- Timeout protection
- Exponential backoff

---

## 📈 Performance Optimizations

### 1. **Connection Pooling**
```go
pool, _ := pgxpool.New(context.Background(), &pgxpool.Config{
    MaxConns:           50,
    MinConns:           10,
    MaxConnLifetime:    time.Hour,
    MaxConnIdleTime:    30 * time.Minute,
    HealthCheckPeriod:  1 * time.Minute,
})
```

### 2. **Caching Strategy**
- Query result caching (Redis)
- Schema caching (in-memory + Redis)
- API key validation caching
- Rate limit counter caching

### 3. **Query Optimization**
- Index hints for complex queries
- LIMIT enforcement on all queries
- Pagination required for large datasets
- Query plan analysis logging

### 4. **Batch Processing**
- Bulk insert operations
- Transaction batching
- Concurrent query execution

---

## 🔄 API Response Format

### Success Response
```json
{
  "success": true,
  "data": {...},
  "meta": {
    "total": 1250,
    "limit": 50,
    "offset": 0,
    "page": 1
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid API key",
    "details": null,
    "request_id": "req-uuid"
  }
}
```

### Error Codes
- `UNAUTHORIZED` - Invalid/expired API key
- `FORBIDDEN` - Insufficient permissions
- `NOT_FOUND` - Resource not found
- `VALIDATION_ERROR` - Invalid input
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `INTERNAL_ERROR` - Server error

---

## 🧪 Testing Requirements

### Unit Tests
- Authentication middleware
- Query builder
- Input validators
- Rate limiter

### Integration Tests
- End-to-end API flows
- Database operations
- Transaction handling

### Security Tests
- SQL injection attempts
- Authentication bypass tests
- Rate limit enforcement
- Project isolation validation

### Load Tests
- Concurrent request handling
- Connection pool exhaustion
- Rate limit accuracy
- Memory leak detection

---

## 📦 Deployment

### Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/cocobase
DB_MAX_CONNECTIONS=50
DB_MIN_CONNECTIONS=10

# Redis Cache
REDIS_URL=redis://localhost:6379
REDIS_DB=0

# Server
PORT=8080
ENV=production
LOG_LEVEL=info

# Security
API_KEY_PREFIX=coco_orm_
JWT_SECRET=...
BCRYPT_COST=12

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW=60s
```

### Docker Deployment
```dockerfile
FROM golang:1.22-alpine AS builder
WORKDIR /app
COPY . .
RUN go build -o orm-server ./cmd/server

FROM alpine:latest
RUN apk --no-cache add ca-certificates
COPY --from=builder /app/orm-server /orm-server
EXPOSE 8080
CMD ["/orm-server"]
```

---

## 🎯 Success Metrics

1. **Performance**: <50ms p95 latency for simple queries
2. **Reliability**: 99.9% uptime
3. **Security**: Zero unauthorized access incidents
4. **Scalability**: Handle 10k requests/second
5. **Developer Experience**: SDKs for top 5 languages within 6 months

---

## 🎉 Complete Backend Solution

With CocoBase ORM, developers can build a **full production backend** using just:

### **Frontend + CocoBase ORM = Complete App**

```
┌─────────────────────────────────────────────────────────────┐
│                     Your Frontend                            │
│         (React, Vue, Angular, Mobile, etc.)                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   CocoBase ORM API                           │
│                                                              │
│  ✅ User Authentication (Login, Register, OAuth)            │
│  ✅ JWT Token Management (Generate, Validate, Rotate)       │
│  ✅ Role-Based Access Control (RBAC)                        │
│  ✅ Permission Management (Collection & Document Level)     │
│  ✅ Session Management (Multi-device, Revocation)           │
│  ✅ Password Management (Reset, Change, Verification)       │
│  ✅ 2FA/TOTP Support                                        │
│  ✅ Email Verification                                       │
│  ✅ User Suspension/Banning                                 │
│  ✅ CRUD Operations (Full Database Access)                  │
│  ✅ Advanced Queries (Filters, Sorting, Pagination)         │
│  ✅ Relationships (Auto-populate, Nested)                   │
│  ✅ Aggregations (Count, Sum, Avg, Group By)               │
│  ✅ Batch Operations (Bulk Create/Update/Delete)            │
│  ✅ Real-time Updates (WebSocket)                           │
│  ✅ File Upload/Storage (via main CocoBase API)             │
│  ✅ Webhooks (Auth events, Custom events)                   │
│  ✅ Audit Logging (Full activity trail)                     │
│  ✅ Rate Limiting (Built-in DDoS protection)                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              PostgreSQL Database (Supabase)                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔥 Example: Full Auth Flow with FastAPI Frontend

```python
# FastAPI frontend example using CocoBase ORM
from fastapi import FastAPI, Request, Depends, HTTPException
import httpx

app = FastAPI()
COCOBASE_ORM_URL = "https://orm.cocobase.com/v1"
ORM_API_KEY = "coco_orm_your-project-id_your-secret"

# Register user
@app.post("/auth/register")
async def register(email: str, password: str, name: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{COCOBASE_ORM_URL}/auth/register",
            headers={"Authorization": f"Bearer {ORM_API_KEY}"},
            json={
                "email": email,
                "password": password,
                "data": {"name": name},
                "roles": ["user"]
            }
        )
        return response.json()

# Login user
@app.post("/auth/login")
async def login(email: str, password: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{COCOBASE_ORM_URL}/auth/login",
            headers={"Authorization": f"Bearer {ORM_API_KEY}"},
            json={"email": email, "password": password}
        )
        return response.json()

# Protected route - validate JWT
async def get_current_user(request: Request):
    token = request.headers.get("Authorization", "").replace("Bearer ", "")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{COCOBASE_ORM_URL}/auth/validate",
            headers={"Authorization": f"Bearer {ORM_API_KEY}"},
            json={"token": token}
        )

        if response.status_code != 200 or not response.json()["data"]["valid"]:
            raise HTTPException(401, "Invalid token")

        return response.json()["data"]

@app.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    return {"user": user}

# Create document with user context
@app.post("/posts")
async def create_post(
    title: str,
    content: str,
    request: Request,
    user: dict = Depends(get_current_user)
):
    user_token = request.headers.get("Authorization", "").replace("Bearer ", "")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{COCOBASE_ORM_URL}/collections/posts/documents",
            headers={
                "Authorization": f"Bearer {ORM_API_KEY}",
                "X-User-Token": user_token
            },
            json={
                "data": {
                    "title": title,
                    "content": content,
                    "author_id": user["user_id"]
                }
            }
        )
        return response.json()
```

**Result:** Full authentication + database access with ~50 lines of code!

---

## 💡 Key Use Cases

### 1. **Rapid MVP Development**
Build a fully functional SaaS in days, not months:
- Frontend framework of choice
- CocoBase ORM for backend
- Deploy frontend anywhere (Vercel, Netlify, etc.)

### 2. **Mobile Apps**
- iOS/Android apps with backend
- JWT auth + refresh tokens
- Offline-first with WebSocket sync
- File uploads via CocoBase Storage API

### 3. **Microservices Architecture**
- Multiple services sharing same user database
- Centralized auth with distributed JWT validation
- Each service can have its own ORM key with specific permissions

### 4. **Multi-tenant Applications**
- Each tenant = one CocoBase project
- Isolated data with project-level scoping
- Tenant-specific JWT secrets
- Custom branding via email templates

### 5. **Admin Dashboards**
- FastAPI/Django/Next.js admin dashboard
- Full user management
- Audit logs for compliance
- Role-based access control

---

## 🚧 Future Enhancements

1. **GraphQL Support**: Alternative query interface
2. **Field-level Encryption**: Encrypt sensitive fields at rest
3. **Multi-region Deployment**: Edge computing support
4. **Offline Sync**: Local-first architecture support with conflict resolution
5. **AI-powered Query Suggestions**: Natural language to query
6. **Time-series Support**: Optimized for time-series data
7. **Geospatial Queries**: Location-based filtering with PostGIS
8. **Event Sourcing**: Full audit trail with event replay
9. **LDAP/SAML Integration**: Enterprise SSO support
10. **WebAuthn/Passkeys**: Passwordless authentication
11. **Rate Limit Customization**: Per-endpoint rate limits
12. **Custom Middleware**: User-defined request/response interceptors
13. **Scheduled Jobs**: Cron-like task scheduling
14. **Bulk Import/Export**: CSV/JSON bulk operations with validation
15. **Data Migrations**: Schema migration tools and versioning

---

## 📚 Documentation Links

- API Reference: `/docs/api-reference.md`
- Authentication Guide: `/docs/authentication.md`
- Query DSL Guide: `/docs/query-dsl.md`
- SDKs: `/docs/sdks.md`
- Examples: `/docs/examples/`

---

**Document Version:** 1.0
**Last Updated:** 2025-01-15
**Status:** Ready for Implementation
