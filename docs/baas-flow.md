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
7. [Performance — Unnecessary Steps to Remove](#7-performance--unnecessary-steps-to-remove)
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

---

## 7. Performance — Unnecessary Steps to Remove

This section lists every redundant or wasteful step found in the hot paths, ranked by impact. Removing or fixing these will directly reduce latency.

---

### Priority 1 — Tier 1 (Highest impact, fix first)

---

#### 1.1 Double DB query after cache hit in `get_project()`

**File:** `app/core/dependencies.py`

When the Redis or in-memory cache returns a hit, the code still fires **two sequential DB queries** — one for `Project` and one for `User` — using the IDs stored in the cache.

```
Cache hit  →  get project_id from cache  →  SELECT Project WHERE id = ...
                                          →  SELECT User WHERE id = ...
```

The whole point of the cache is to avoid DB queries. On a cache hit, the cached `project_id` and `user_id` should be enough to satisfy downstream code. Either:
- Store the full lightweight project data in cache and skip the DB queries entirely, OR
- Replace the two separate queries with a single join query.

**Current operation count:** 2 DB queries even on a cache hit.
**Target:** 0 DB queries on a cache hit.

---

#### 1.2 In-memory cache is reset on every single request

**File:** `app/core/dependencies.py`

After resolving a project (even from Redis cache), the code unconditionally writes the result back into the in-memory LRU cache, resetting its TTL. On high traffic this causes **constant cache churn** — entries never stay warm because every request refreshes them, pushing out other entries via LRU eviction.

Fix: only write to in-memory cache when the value was NOT already there (a real miss), not on every request.

---

#### 1.3 `print()` statements inside the query filter builder

**File:** `app/api/collections/utilities.py`

Every request that uses query filters (nearly all `GET /collections/.../documents` calls) hits `build_query_filters()`, which contains multiple `print()` statements that dump debug info to stdout. This is **synchronous I/O on every request** that goes to the console even in production.

```
print(f"DEBUG: Processing param: {key}={value}")
print(f"DEBUG: Created filter - {field_expr} {operator} {typed_value}")
```

Remove or replace with `logging.debug(...)` (which is a no-op when log level is INFO/WARNING in production).

---

#### 1.4 File uploads block the request thread during signup/create-document

**File:** `app/api/auth_collection.py`, `app/api/collections/collections.py`

When a user signs up or creates a document with file attachments, the upload happens **synchronously inside the request handler** before the user/document is even created:

```
1. Read file bytes (I/O)
2. Check storage quota (DB query)
3. Upload to cloud storage (network I/O — can take 200ms–2s)
4. THEN create the user/document
```

The request is held open until the upload completes. If the upload is slow, so is every signup. File processing should either be moved to a background task after the user is created, or uploads should be accepted by a separate endpoint.

---

### Priority 2 — Tier 2 (Significant, fix next)

---

#### 2.1 Login: two sequential 2FA queries that could be one

**File:** `app/api/auth_collection.py`

When 2FA is enabled, login runs two queries back-to-back:

```
1. SELECT TwoFactorSettings WHERE user_id = ... AND is_enabled = True
2. (if settings found) SELECT TwoFactorCode WHERE user_id = ... AND ...
```

These can be collapsed into a single query with a join, or the first query can be skipped entirely since 2FA enablement can be stored as a flag directly on the user row, avoiding the extra table lookup.

---

#### 2.2 Signup: duplicate queries checking the user count and user existence

**File:** `app/api/auth_collection.py`

Signup runs these two separate queries with overlapping filters:

```
1. SELECT COUNT(*) FROM app_users WHERE client_id = ?   ← plan limit check
2. SELECT * FROM app_users WHERE client_id = ? AND email = ?  ← duplicate check
```

Both hit the `app_users` table with `client_id` as the base filter. The email existence check could be combined with the count query (e.g. `GROUP BY` or a single query that returns both the count and whether the email exists), cutting one round-trip.

---

#### 2.3 `get_collection_by_id_or_name()` fires up to three queries on a miss

**File:** `app/api/collections/utilities.py`

When resolving a collection by name, the helper tries three successive queries:

```
1. SELECT collection WHERE name = exact_name
2. SELECT collection WHERE name = singular_form   (if #1 misses)
3. SELECT collection WHERE name = plural_form     (if #2 misses)
```

All three can be collapsed into a single `WHERE name IN (exact, singular, plural)` query with `ORDER BY CASE` to pick preference. One round-trip instead of three.

---

#### 2.4 Collection resolved multiple times in the same request

**File:** `app/api/collections/collections.py`, `app/api/collections/utilities.py`

In `list_documents()` and `get_document()`, the collection is fetched from the database at the start of the handler. Then, if relationship population is requested (`?populate=...`), `AutoRelationshipResolver._get_collection_by_name()` fetches the **same collection again** (up to 3 queries, see 2.3 above).

The already-loaded collection object should be passed through to the resolver rather than re-fetching it.

---

#### 2.5 `db.merge()` called on every cache hit for app users

**File:** `app/core/dependencies.py`

When `get_app_user()` finds the user in the in-memory cache, it calls `db.merge(app_user, load=False)` to re-attach the cached ORM object to the current DB session. This adds SQLAlchemy overhead on every authenticated request even though the user data has not changed.

Fix: either store a plain dict in the cache (not an ORM object) and reconstruct the user without `merge()`, or only call `merge()` when the session is actually going to write.

---

#### 2.6 Eager-load of collection inside `get_document()` when it was already fetched

**File:** `app/api/collections/collections.py`

In `get_document()`, the collection is fetched first (to resolve it by name/ID), and then the document query adds `joinedload(Document.collection)` — causing PostgreSQL to return the collection row a second time in the same request.

Since the collection object is already in scope, the `joinedload` is not needed. Remove it and attach the already-loaded collection manually.

---

### Priority 3 — Tier 3 (Lower impact, but worth fixing)

---

#### 3.1 Separate `COUNT` query on every document list

**File:** `app/api/collections/collections.py`

`list_documents()` runs a `COUNT(*)` query separately from the data fetch query to calculate pagination totals. This doubles the number of queries on every list call. For large collections this is a full table scan.

Options:
- Use PostgreSQL `COUNT(*) OVER()` window function to get the total in the same query.
- Cache the count with a short TTL.
- Make total count opt-in (`?count=true`) so it is only paid when the client needs it.

---

#### 3.2 N+1 queries when populating nested relationships

**File:** `app/api/collections/utilities.py`

When `?populate=field` is used and the populated documents themselves have nested populate fields, the resolver recurses into `_populate_relationships()` for each document individually. With 50 documents and nested relationships, this can trigger 50+ additional queries.

Fix: batch the nested lookups — collect all IDs across all documents first, fetch them in one `WHERE id IN (...)` query, then map results back.

---

#### 3.3 Silent auto-creation of collections on name typos

**File:** `app/api/collections/utilities.py`

`get_collection_by_id_or_name()` creates a new collection automatically if none is found. This means a typo in the collection name (`?collection=prducts` instead of `products`) silently creates an empty `prducts` collection in the database. This is not a performance issue but it causes real data correctness problems and pollutes the project with ghost collections.

The auto-create should be limited to specific endpoints (e.g. `POST /documents`) and disabled on read-only endpoints (`GET /documents`).

---

#### 3.4 EmailService instantiated twice during signup

**File:** `app/api/auth_collection.py`

When both `SEND_WELCOME_EMAIL` and `ENABLE_EMAIL_VERIFICATION` are enabled, `EmailService` is constructed twice inside the same request:

```python
email_service = EmailService(project_id=project.id, db=db)  # welcome email
# ...
email_service = EmailService(project_id=project.id, db=db)  # verification email
```

Instantiate it once and reuse it for both sends.

---

### Summary Table

| # | File | Issue | Queries/ops wasted | Priority |
|---|------|-------|--------------------|----------|
| 1.1 | `dependencies.py` | 2 DB queries on every cache hit | 2 DB round-trips | **Tier 1** |
| 1.2 | `dependencies.py` | In-memory cache reset on every request | Cache thrashing | **Tier 1** |
| 1.3 | `utilities.py` | `print()` debug I/O in production | stdout write per request | **Tier 1** |
| 1.4 | `auth_collection.py` | File upload blocks request thread | 200ms–2s latency spike | **Tier 1** |
| 2.1 | `auth_collection.py` | 2 sequential 2FA queries | 1 extra DB query | **Tier 2** |
| 2.2 | `auth_collection.py` | Duplicate user count + existence check | 1 extra DB query | **Tier 2** |
| 2.3 | `utilities.py` | Triple fallback collection lookup | 2 extra DB queries | **Tier 2** |
| 2.4 | `collections.py` | Collection re-fetched inside relationship resolver | 1–3 extra DB queries | **Tier 2** |
| 2.5 | `dependencies.py` | `db.merge()` on every auth'd request | SQLAlchemy overhead | **Tier 2** |
| 2.6 | `collections.py` | `joinedload(collection)` when already loaded | 1 extra join | **Tier 2** |
| 3.1 | `collections.py` | Separate `COUNT` query on every list | 1 extra DB query | **Tier 3** |
| 3.2 | `utilities.py` | N+1 on nested relationship populate | N extra queries | **Tier 3** |
| 3.3 | `utilities.py` | Auto-create on name miss (data integrity) | 1 extra write | **Tier 3** |
| 3.4 | `auth_collection.py` | EmailService constructed twice | Object overhead | **Tier 3** |
