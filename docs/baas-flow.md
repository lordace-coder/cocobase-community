# CocoBase BaaS — Client Flow Documentation

This document explains what happens under the hood when client applications (using an `x-api-key`) interact with the two main public API surfaces: **Auth Collection routes** and **Collection routes**.

---

## Table of Contents

1. [Overview — How the x-api-key Works](#1-overview--how-the-x-api-key-works)
2. [Auth Collection Routes](#2-auth-collection-routes)
   - [Signup](#21-signup)
   - [Login](#22-login)
   - [Logout](#23-logout)
   - [2FA Verification](#24-2fa-verification)
3. [Collection Routes](#3-collection-routes)
   - [List Collections / Get Documents](#31-list-documents)
   - [Create Document](#32-create-document)
   - [Get a Single Document](#33-get-a-single-document)
   - [Update a Document](#34-update-a-document)
   - [Delete a Document](#35-delete-a-document)
4. [Permission System](#4-permission-system)
5. [Query Filters Reference](#5-query-filters-reference)
6. [End-to-End Flow Diagrams](#6-end-to-end-flow-diagrams)

---

## 1. Overview — How the `x-api-key` Works

Every request from your client app must include the project's API key in a header:

```
x-api-key: <your-project-api-key>
```

### What happens on every request

```
Client request (with x-api-key header)
         │
         ▼
get_project() dependency  [app/core/dependencies.py]
         │
         ├─► Check Redis cache  →  key: "project_data:{api_key}"  (TTL 60 s)
         │         cache hit ──────────────────────────────────────────┐
         │                                                              │
         ├─► Cache miss: query DB for Project where api_key matches    │
         │         • Project must be active = True                     │
         │         • Request origin must be in allowed_origins         │
         │                                                              │
         ├─► Populate Redis & in-memory cache                          │
         │                                                              ▼
         └─► Increment API usage counter → return (Project, Owner)
```

**Cache layers (fastest → slowest)**

| Layer | TTL | Max entries | Notes |
|-------|-----|-------------|-------|
| Redis | 60 s | — | Distributed, survives restarts |
| In-memory (LRU) | 60 s | 10 000 | Fallback when Redis is down |
| Database | — | — | Source of truth |

The resolved `Project` object is passed to every route handler, so routes know which project the request belongs to without an extra DB query.

---

## 2. Auth Collection Routes

Base path: `/auth-collections`
All routes require `x-api-key`.

---

### 2.1 Signup

```
POST /auth-collections/signup
Headers: x-api-key: <key>
Body (JSON or multipart/form-data):
  {
    "email":    "user@example.com",
    "password": "secret",
    ...any additional custom fields...
  }
```

**Full flow**

```
Validate x-api-key  →  get_project()
         │
         ▼
Check required fields (email + password)
         │
         ▼
Duplicate email check per project
         │
         ▼
Plan limit check  (project.configs.max_users)
   ├─ >100 % → deactivate project, return 403
   ├─ >90 %  → warning logged
   └─ >80 %  → warning logged
         │
         ▼
File uploads (if multipart)
   └─ Upload files to cloud storage (Cloudinary / S3)
   └─ Replace form fields with returned URLs
         │
         ▼
Role filtering  (project.configs.ALLOWED_SELF_ROLES)
   └─ Strip any roles the caller is not allowed to self-assign
         │
         ▼
Create AppUser  →  bcrypt-hash password  →  save to DB
         │
         ▼
Background tasks (non-blocking):
   ├─ Send welcome email   (if SEND_WELCOME_EMAIL = true)
   └─ Send verification email (if ENABLE_EMAIL_VERIFICATION = true)
         │
         ▼
create_app_user_token(user)  →  JWT signed with project_id, expires in 2 days
         │
         ▼
Response 201:
  {
    "access_token": "<jwt>",
    "user": { ...AppUser fields... }
  }
```

---

### 2.2 Login

```
POST /auth-collections/login
Headers: x-api-key: <key>
Body (JSON):
  {
    "email":    "user@example.com",
    "password": "secret"
  }
```

**Full flow**

```
Validate x-api-key  →  get_project()
         │
         ▼
Query AppUser by (project_id + email)
   └─ Not found → 404 "Account with this email does not exist"
         │
         ▼
compare_password(payload.password, user.password)
   └─ Mismatch → 400 "Invalid password value"
         │
         ▼
Is 2FA enabled? (project.configs.ENABLE_2FA + user TwoFactorSettings)
   │
   ├─ NO  ──────────────────────────────────────────────────────┐
   │                                                             │
   └─ YES                                                        │
       │                                                         │
       ▼                                                         │
   Recent 2FA verified? (within last 5 min)                     │
       ├─ YES  ───────────────────────────────────────────────── ┤
       └─ NO                                                      │
           │                                                      │
           ▼                                                      │
       Active OTP exists for this user?                          │
           ├─ YES & sent < 2 min ago → return existing message   │
           └─ NO (or expired)                                     │
               │                                                  │
               ▼                                                  │
           Generate OTP (length from OTP_LENGTH config, 4-10)   │
           Send OTP via email  →  save to DB (expires 10 min)   │
           Return: { "requires_2fa": true, "message": "..." }   │
                                                                  │
                                                          ◄───────┘
                                                          │
                                                          ▼
                                        create_app_user_token(user)
                                                          │
                                                          ▼
                                        Response 200:
                                          {
                                            "access_token": "<jwt>",
                                            "user": { ...AppUser fields... }
                                          }
```

---

### 2.3 Logout

CocoBase uses **stateless JWT tokens**.  There is no server-side session to invalidate.

Logout is handled entirely on the **client side**:

1. Delete the stored `access_token` (localStorage, secure cookie, etc.).
2. Stop including it in request headers.

Tokens automatically expire after **2 days** from issue time.

> **Tip:** If you need forced logout (e.g. password change, suspicious activity), you can rotate the project's API key from the dashboard. All outstanding tokens become invalid because they are signed with the project ID.

---

### 2.4 2FA Verification

```
POST /auth-collections/verify-2fa
Headers: x-api-key: <key>
Body (JSON):
  {
    "email": "user@example.com",
    "code":  "123456"
  }
```

```
Validate x-api-key  →  get_project()
         │
         ▼
Look up pending OTP for (project_id + email + code)
   └─ Not found or expired → 400 "Invalid or expired code"
         │
         ▼
Mark OTP as used  →  record 2FA verified timestamp on user
         │
         ▼
create_app_user_token(user)
         │
         ▼
Response 200:
  {
    "access_token": "<jwt>",
    "user": { ...AppUser fields... }
  }
```

---

### Authenticated requests after login

Once the client has an `access_token` it should include it on every request that touches protected resources:

```
Authorization: Bearer <access_token>
x-api-key: <key>
```

The `get_app_user()` dependency decodes and validates the JWT, resolving the correct `AppUser` for permission checks.

---

## 3. Collection Routes

Base path: `/collections`
All routes require `x-api-key`.
Some operations also require `Authorization: Bearer <token>` depending on collection permissions.

---

### 3.1 List Documents

```
GET /collections/{collection_id_or_name}/documents
Headers:
  x-api-key: <key>
  Authorization: Bearer <token>   (only if collection is not public-read)

Query params (all optional):
  ?limit=50&page=1&sort_by=created_at&sort_order=desc
  &<field>=<value>          (filter)
  &populate=<relation_field>
```

**Full flow**

```
Validate x-api-key  →  get_project()
         │
         ▼
Resolve collection:
   ├─ Try by ID first
   └─ Fall back to name lookup (auto-creates collection if not found)
         │
         ▼
can_access_collection(collection, "read", app_user)
   ├─ No permissions set on collection  →  public, allow
   ├─ Permissions set, no token         →  401
   └─ Token present, role matches       →  allow
         │
         ▼
Build SQLAlchemy query:
   ├─ Parse query params → filters  [app/api/collections/utilities.py]
   ├─ Apply pagination  (default limit 50, max 500)
   └─ Apply sort (default: created_at DESC)
         │
         ▼
Optional: Populate relationships
   └─ Detect "<field_id>" pattern → eager-load from "<field>" collection
         │
         ▼
Response 200:
  [
    { "id": "...", "data": {...}, "created_at": "..." },
    ...
  ]
```

---

### 3.2 Create Document

```
POST /collections/documents
Headers:
  x-api-key: <key>
  Authorization: Bearer <token>   (if collection requires it)
  Content-Type: application/json  (or multipart/form-data for file uploads)

Body:
  {
    "collection": "posts",      ← collection name or id
    "title": "Hello World",
    "body":  "..."
  }
```

**Full flow**

```
Validate x-api-key  →  get_project()
         │
         ▼
Detect content type:
   ├─ JSON  →  parse body directly
   └─ Multipart form-data  →  extract fields + files
         │
         ▼
File uploads (if any):
   ├─ Check project storage quota
   └─ Upload to cloud storage → replace field values with URLs
         │
         ▼
Resolve / auto-create collection by name or ID
         │
         ▼
can_access_collection(collection, "create", app_user)
         │
         ▼
Create Document(data=doc_data, collection_id=...)  →  DB commit
         │
         ▼
Trigger events (background):
   ├─ Webhook (if collection.webhook_url set)
   └─ Watchers / real-time listeners
         │
         ▼
Response 201:
  { "id": "...", "data": {...}, "created_at": "..." }
```

---

### 3.3 Get a Single Document

```
GET /collections/{collection_id_or_name}/documents/{document_id}
Headers:
  x-api-key: <key>
  Authorization: Bearer <token>   (if required by permissions)

Query params (optional):
  ?populate=<relation_field>
```

```
Validate x-api-key  →  get_project()
         │
         ▼
Resolve collection  →  can_access_collection("read", app_user)
         │
         ▼
Query Document by (id + collection_id)
   └─ Not found → 404
         │
         ▼
Optional: eager-load relationship via populate
         │
         ▼
Response 200:
  { "id": "...", "data": {...}, ... }
```

---

### 3.4 Update a Document

```
PATCH /collections/{collection_id_or_name}/documents/{document_id}
Headers:
  x-api-key: <key>
  Authorization: Bearer <token>   (if required)
Body (JSON):
  {
    "field_name": "new value",

    "$append": { "tags": ["fastapi", "baas"] },   ← add items to array
    "$remove": { "tags": ["old-tag"] }             ← remove items from array
  }
```

```
Validate x-api-key  →  get_project()
         │
         ▼
Resolve collection  →  can_access_collection("update", app_user)
         │
         ▼
Fetch existing Document
   └─ Not found → 404
         │
         ▼
Apply operations (in order):
   1. $remove  →  pull items from existing arrays
   2. $append  →  push new items into arrays
   3. Regular fields  →  shallow merge into data JSONB
         │
         ▼
DB commit  →  return updated document
```

---

### 3.5 Delete a Document

```
DELETE /collections/{collection_id_or_name}/documents/{document_id}
Headers:
  x-api-key: <key>
  Authorization: Bearer <token>   (if required)
```

```
Validate x-api-key  →  get_project()
         │
         ▼
Resolve collection  →  can_access_collection("delete", app_user)
         │
         ▼
Delete Document  →  DB commit
         │
         ▼
Response 200:
  { "status": "success" }
```

---

## 4. Permission System

Each collection stores a `permissions` object (JSONB):

```json
{
  "create": ["admin", "editor"],
  "read":   [],
  "update": ["admin"],
  "delete": ["admin"]
}
```

**Resolution rules**

| Scenario | Result |
|---|---|
| `permissions` is `null` or `{}` | All operations open to everyone |
| Permission list for an operation is `[]` (empty) | That operation is public (no token needed) |
| Permission list has roles, no `Authorization` header sent | **401 Unauthorized** |
| `Authorization` token present, user role is in the list | **Allowed** |
| `Authorization` token present, user role is NOT in the list | **403 Forbidden** |

User roles are stored in `app_users.roles` (string array) and set at signup or by admin update.

---

## 5. Query Filters Reference

Filters are passed as query parameters to list endpoints.

### Basic equality

```
GET /collections/products/documents?status=active&category=electronics
```

### Comparison operators

Append the operator with `_` after the field name:

| Suffix | Meaning | Example |
|--------|---------|---------|
| `_gt`  | greater than | `?price_gt=100` |
| `_gte` | greater than or equal | `?price_gte=100` |
| `_lt`  | less than | `?price_lt=500` |
| `_lte` | less than or equal | `?price_lte=500` |
| `_ne`  | not equal | `?status_ne=archived` |
| `_contains` | substring match | `?name_contains=john` |
| `_startswith` | prefix match | `?slug_startswith=news-` |
| `_endswith` | suffix match | `?email_endswith=@gmail.com` |
| `_in` | value in list | `?status_in=active,pending` |
| `_notin` | value not in list | `?role_notin=banned,suspended` |
| `_isnull` | is null / is not null | `?deleted_at_isnull=true` |

### OR conditions

```
GET /collections/users/documents?[or]role=admin&[or]isPremium=true
```

### Multi-field OR on the same value

```
GET /collections/users/documents?name__or__email_contains=john
```

### Relationship filter + populate

```
GET /collections/posts/documents?author.role=admin&populate=author
```

Detects `author_id` field in documents, joins to the `author` collection, filters by `author.role`, and returns the full author object embedded.

### Pagination & sorting

```
?limit=20&page=2&sort_by=created_at&sort_order=asc
```

Default limit: 50. Maximum limit: 500.

---

## 6. End-to-End Flow Diagrams

### Signup → Login → Fetch Documents

```
Client App                           CocoBase API                         Database
    │                                      │                                  │
    │── POST /auth-collections/signup ─────►│                                  │
    │   x-api-key: <key>                   │── validate key ──────────────────►│
    │   {email, password, name}            │◄─ project returned ───────────────│
    │                                      │── INSERT app_user ────────────────►│
    │◄─ {access_token, user} ─────────────│◄─ new user ───────────────────────│
    │                                      │                                  │
    │── POST /auth-collections/login ──────►│                                  │
    │   x-api-key: <key>                   │── validate key ──────────────────►│
    │   {email, password}                  │── SELECT app_user by email ───────►│
    │                                      │◄─ user row ───────────────────────│
    │                                      │── bcrypt.verify(password) ──────  │
    │◄─ {access_token, user} ─────────────│                                  │
    │                                      │                                  │
    │── GET /collections/posts/documents ──►│                                  │
    │   x-api-key: <key>                   │── validate key ──────────────────►│
    │   Authorization: Bearer <token>      │── decode JWT ──────────────────── │
    │                                      │── check permissions ─────────────►│
    │                                      │── SELECT documents ───────────────►│
    │◄─ [{id, data, created_at}, ...] ────│◄─ document rows ──────────────────│
    │                                      │                                  │
```

### Login with 2FA enabled

```
Client App                           CocoBase API                         Email Service
    │                                      │                                  │
    │── POST /auth-collections/login ──────►│                                  │
    │   {email, password}                  │── password OK                    │
    │                                      │── 2FA enabled, no recent verify  │
    │                                      │── generate OTP ──────────────────►│
    │◄─ {requires_2fa: true, message} ────│                                   │── send email
    │                                      │                                  │
    │── POST /auth-collections/verify-2fa ─►│                                  │
    │   {email, code: "123456"}            │── validate OTP, not expired      │
    │                                      │── mark OTP used                  │
    │◄─ {access_token, user} ─────────────│                                  │
    │                                      │                                  │
```

---

## Key Files Reference

| File | Purpose |
|------|---------|
| `app/api/auth_collection.py` | Login, signup, 2FA, OAuth endpoints |
| `app/api/collections/collections.py` | Document CRUD endpoints |
| `app/api/collections/utilities.py` | Query filter builder, collection resolver |
| `app/core/dependencies.py` | `get_project()`, `get_app_user()` dependencies |
| `app/core/permissions.py` | `can_access_collection()` RBAC logic |
| `app/models/app_user.py` | AppUser ORM model + password hashing |
| `app/models/collection.py` | Collection ORM model |
| `app/models/document.py` | Document ORM model (JSONB data) |
| `app/services/jwt.py` | JWT create/decode helpers |
| `app/services/oauth_service.py` | OAuth find-or-create logic |
| `app/main.py` | FastAPI app + router registration |
