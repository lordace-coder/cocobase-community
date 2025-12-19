# CocoBase ORM - Quick Reference

**Complete specification:** See `COCOBASE_ORM_MICROSERVICE_SPEC.md`

---

## 🎯 What It Does

CocoBase ORM is a **complete backend-as-a-service** built in Go that provides:

1. **Full Authentication System** (like Auth0/Firebase Auth)
2. **Database ORM** (like Prisma/TypeORM via REST)
3. **Role-Based Access Control** (RBAC)
4. **Real-time Subscriptions** (WebSocket)
5. **File Storage Integration** (via main CocoBase API)

---

## 🔑 Authentication Features

### User Management
- ✅ Register, Login, Logout
- ✅ OAuth (Google, GitHub, Apple, Facebook, Twitter)
- ✅ JWT token generation & validation
- ✅ Refresh tokens with device tracking
- ✅ Password reset flow
- ✅ Email verification
- ✅ 2FA/TOTP support
- ✅ Session management (multi-device)
- ✅ User suspension/banning
- ✅ Custom JWT secrets per project

### Role & Permission System
- ✅ Assign/remove roles
- ✅ Collection-level permissions
- ✅ Check user permissions
- ✅ Custom role definitions

### Configuration
- ✅ Generate/rotate JWT secrets
- ✅ Configure OAuth providers
- ✅ Set up webhooks for auth events
- ✅ Email templates for notifications
- ✅ Custom password policies

---

## 💾 Database Features

### CRUD Operations
- Create, Read, Update, Delete documents
- Batch operations (bulk create/update/delete)
- Array operations ($append, $remove)

### Advanced Queries
- Complex filters with boolean logic
- Comparison operators (gte, lt, contains, in, etc.)
- Sorting and pagination
- Relationship population (auto-JOIN)
- Full-text search

### Aggregations
- Count, Sum, Avg, Min, Max
- Group by operations

### Real-time
- WebSocket subscriptions to collections
- Event notifications (create, update, delete)

---

## 🗄️ New Database Tables (14 tables)

1. **orm_api_keys** - ORM access keys for projects
2. **project_auth_config** - JWT secrets & auth settings
3. **oauth_providers** - OAuth provider configurations
4. **refresh_tokens** - User refresh tokens with device info
5. **password_reset_tokens** - Password reset tokens
6. **email_verification_tokens** - Email verification tokens
7. **user_sessions** - Active user sessions
8. **webhook_configs** - Webhook URLs for events
9. **webhook_logs** - Webhook delivery logs
10. **email_configs** - Email provider settings
11. **email_templates** - Customizable email templates
12. **user_api_keys** - End-user API keys
13. **totp_secrets** - 2FA secrets and backup codes
14. **audit_logs** - Complete audit trail

**Plus:** Updates to `app_users` table (add email_verified, suspended, last_login_at, etc.)

---

## 🔐 Security Features

1. **Multi-layer Authentication**
   - ORM API key (project-level)
   - JWT token (user-level)
   - API keys (machine-to-machine)

2. **Project Isolation**
   - All queries auto-scoped to project_id
   - Zero cross-project data leakage

3. **Rate Limiting**
   - Per-key rate limits
   - Plan-based limits
   - Burst protection

4. **Input Validation**
   - SQL injection prevention (parameterized queries only)
   - JSON payload validation
   - Field name whitelisting

5. **Audit Logging**
   - Every operation logged
   - IP address tracking
   - User agent tracking

---

## 🚀 Example Architecture

```
┌─────────────────┐
│  React/Vue/     │
│  Mobile App     │
└────────┬────────┘
         │
         │ HTTPS
         │
┌────────▼────────────────────────────────────┐
│        CocoBase ORM (Go)                    │
│                                             │
│  🔐 Validates ORM Key                      │
│  🎫 Generates/Validates JWT                │
│  👤 Manages Users & Roles                  │
│  📝 CRUD Operations                        │
│  🔍 Advanced Queries                       │
│  📊 Aggregations                           │
│  🔔 WebSocket Real-time                    │
│  📧 Email Notifications                    │
└────────┬────────────────────────────────────┘
         │
         │ PostgreSQL
         │
┌────────▼────────┐
│   Supabase DB   │
└─────────────────┘
```

---

## 📝 Usage Example

### 1. Generate ORM Key (from main CocoBase API)
```bash
POST https://api.cocobase.com/projects/{project_id}/orm-keys
Authorization: Bearer {main_api_key}

Response: {
  "key": "coco_orm_project-123_abc...def",
  "permissions": {...}
}
```

### 2. Register User
```bash
POST https://orm.cocobase.com/v1/auth/register
Authorization: Bearer coco_orm_project-123_abc...def

{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "data": {"name": "John Doe"},
  "roles": ["user"]
}

Response: {
  "user": {...},
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc..."
}
```

### 3. Create Document (with user context)
```bash
POST https://orm.cocobase.com/v1/collections/posts/documents
Authorization: Bearer coco_orm_project-123_abc...def
X-User-Token: eyJhbGc... (user's JWT)

{
  "data": {
    "title": "My Post",
    "content": "Hello world",
    "author_id": "user-uuid"
  }
}
```

### 4. Query with Filters & Population
```bash
GET https://orm.cocobase.com/v1/collections/posts/documents?status=published&author.role=admin&populate=author&limit=20
Authorization: Bearer coco_orm_project-123_abc...def
X-User-Token: eyJhbGc...
```

---

## 🛠️ Tech Stack

- **Language:** Go 1.22+
- **Web Framework:** Fiber v3
- **Database:** PostgreSQL (pgx driver)
- **Cache:** Redis
- **Authentication:** JWT (HS256/RS256)
- **Password Hashing:** bcrypt
- **2FA:** TOTP (RFC 6238)
- **WebSocket:** Fiber WebSocket

---

## 📦 Go Packages Needed

```go
// Core
"github.com/gofiber/fiber/v3"
"github.com/jackc/pgx/v5/pgxpool"
"github.com/redis/go-redis/v9"

// Auth
"github.com/golang-jwt/jwt/v5"
"golang.org/x/crypto/bcrypt"
"github.com/pquerna/otp/totp"

// Utilities
"github.com/go-playground/validator/v10"
"github.com/goccy/go-json"
"go.uber.org/zap"
"github.com/spf13/viper"
```

---

## 🎯 Implementation Priority

### Phase 1: Core (MVP)
1. Project isolation & ORM key validation
2. Basic CRUD operations
3. Simple filtering & pagination
4. User registration & login
5. JWT generation & validation
6. Basic RBAC

### Phase 2: Advanced Auth
1. OAuth integration
2. Refresh tokens
3. Password reset flow
4. Email verification
5. Session management
6. 2FA/TOTP

### Phase 3: Advanced Features
1. Complex queries (OR groups, relationships)
2. Aggregations
3. Batch operations
4. WebSocket subscriptions
5. Webhooks
6. Email sending

### Phase 4: Production Ready
1. Audit logging
2. Rate limiting
3. Comprehensive tests
4. Performance optimization
5. Documentation
6. SDKs (JS, Python, etc.)

---

## 🔒 Security Checklist

- [x] All queries parameterized (no SQL injection)
- [x] All secrets encrypted at rest
- [x] All sensitive data hashed (passwords, tokens)
- [x] Project isolation enforced
- [x] Rate limiting per key
- [x] JWT signature validation
- [x] HTTPS only
- [x] CORS configuration
- [x] Input validation
- [x] Audit logging
- [x] Session timeout
- [x] Failed login tracking
- [x] Account lockout after N attempts

---

## 📊 Database Size Estimate

**New Tables:** ~14 tables
**Updated Tables:** 1 table (app_users)
**Indexes:** ~35 new indexes
**Estimated Storage:**
- Small project (1k users): ~50 MB
- Medium project (100k users): ~5 GB
- Large project (1M users): ~50 GB

---

## 🌟 Competitive Advantage

| Feature | CocoBase ORM | Firebase | Supabase | Auth0 | Prisma |
|---------|--------------|----------|----------|-------|--------|
| **Auth** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Database ORM** | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Custom JWT Secret** | ✅ | ❌ | ❌ | ❌ | N/A |
| **Webhooks** | ✅ | ✅ | ✅ | ✅ | ❌ |
| **2FA** | ✅ | ✅ | ✅ | ✅ | N/A |
| **Audit Logs** | ✅ | Limited | ✅ | ✅ | ❌ |
| **Multi-tenant** | ✅ | Limited | ✅ | ✅ | ❌ |
| **Self-hosted** | ✅ | ❌ | ✅ | ❌ | ✅ |
| **Language** | Go | Cloud | Cloud | Cloud | Node.js |
| **Performance** | ⚡⚡⚡ | ⚡⚡ | ⚡⚡ | ⚡⚡ | ⚡⚡ |

**Key Differentiator:** CocoBase ORM gives you **complete control** over your backend while being as easy to use as Firebase.

---

**Last Updated:** 2025-01-18
**Version:** 1.0
**Status:** Ready for Implementation
