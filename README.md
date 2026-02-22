# COCOBASE - Complete Backend as a Service (BaaS) Platform

## 📚 Table of Contents
- [Introduction](#introduction)
- [Quick Start](#quick-start)
- [Authentication & Users](#authentication--users)
- [Collections & Documents](#collections--documents)
- [File Storage](#file-storage)
- [Real-time Features](#real-time-features)
- [Advanced Features](#advanced-features)
- [ORM Features & Recommendations](#orm-features--recommendations)
- [Missing Features & Roadmap](#missing-features--roadmap)

---

## Introduction

**COCOBASE** is a robust, production-ready Backend as a Service (BaaS) platform that provides everything you need to build modern applications without managing infrastructure.

**Base URL:** `https://api.cocobase.buzz`

### What is BaaS?
Backend as a Service (BaaS) provides ready-made backend functionality like:
- User authentication
- Database (NoSQL collections)
- File storage
- Real-time updates
- Webhooks & integrations
- And more!

Think of it as Firebase, Supabase, or Parse - but built with FastAPI and PostgreSQL.

---

## Quick Start

### 1. Create a Project
First, create a project to get your API key:

```bash
POST https://api.cocobase.buzz/project/
Content-Type: application/json
Authorization: Bearer YOUR_USER_TOKEN

{
  "name": "My Awesome App"
}
```

**Response:**
```json
{
  "id": "project-123",
  "name": "My Awesome App",
  "api_key": "coco_live_abc123xyz..."
}
```

### 2. Use Your API Key
All subsequent requests use your project's API key:

```bash
# Set as header
x-api-key: coco_live_abc123xyz...
```

---

## Authentication & Users

### App User Authentication
Your app's end-users (customers, members) authenticate through the `/auth-collections` endpoints.

### Register a New User

**Endpoint:** `POST /auth-collections/signup`

**Simple Registration (JSON):**
```bash
POST https://api.cocobase.buzz/auth-collections/signup
Content-Type: application/json
x-api-key: YOUR_API_KEY

{
  "email": "user@example.com",
  "password": "securePassword123",
  "username": "johndoe",
  "age": 25
}
```

**Registration with File Upload (Multipart):**
```bash
POST https://api.cocobase.buzz/auth-collections/signup
Content-Type: multipart/form-data
x-api-key: YOUR_API_KEY

data: {"email": "user@example.com", "password": "securePassword123"}
avatar: @profile.jpg
cover_photo: @cover.png
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Login User

**Endpoint:** `POST /auth-collections/login`

```bash
POST https://api.cocobase.buzz/auth-collections/login
Content-Type: application/json
x-api-key: YOUR_API_KEY

{
  "email": "user@example.com",
  "password": "securePassword123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Get Current User

**Endpoint:** `GET /auth-collections/user`

```bash
GET https://api.cocobase.buzz/auth-collections/user
Authorization: Bearer USER_ACCESS_TOKEN
x-api-key: YOUR_API_KEY
```

**Response:**
```json
{
  "id": "user-456",
  "email": "user@example.com",
  "data": {
    "username": "johndoe",
    "age": 25
  },
  "created_at": "2025-01-15T10:00:00",
  "roles": ["user"]
}
```

### Update Current User

**Endpoint:** `PATCH /auth-collections/user`

**JSON Update:**
```bash
PATCH https://api.cocobase.buzz/auth-collections/user
Content-Type: application/json
Authorization: Bearer USER_ACCESS_TOKEN
x-api-key: YOUR_API_KEY

{
  "username": "john_updated",
  "bio": "Software developer"
}
```

**Update with File Upload:**
```bash
PATCH https://api.cocobase.buzz/auth-collections/user
Content-Type: multipart/form-data
Authorization: Bearer USER_ACCESS_TOKEN
x-api-key: YOUR_API_KEY

data: {"bio": "Updated bio"}
avatar: @new_avatar.jpg
```

### List All Users (Admin)

**Endpoint:** `GET /auth-collections/users`

```bash
GET https://api.cocobase.buzz/auth-collections/users?limit=50&offset=0
x-api-key: YOUR_API_KEY
```

**Advanced Filtering:**
```bash
# Filter by role
GET /auth-collections/users?data.role=admin

# Filter by age range
GET /auth-collections/users?data.age_gte=18&data.age_lte=65

# Search by email or username
GET /auth-collections/users?email__or__data.username_contains=john

# Sort by creation date
GET /auth-collections/users?sort=created_at&order=desc
```

**Response:**
```json
{
  "data": [
    {
      "id": "user-123",
      "email": "user@example.com",
      "data": { "username": "johndoe", "age": 25 },
      "created_at": "2025-01-15T10:00:00",
      "roles": ["user"]
    }
  ],
  "total": 100,
  "limit": 50,
  "offset": 0,
  "has_more": true
}
```

### Google OAuth Login

**Step 1: Get OAuth URL**
```bash
GET https://api.cocobase.buzz/auth-collections/login-google
x-api-key: YOUR_API_KEY
```

**Response:**
```json
{
  "url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

**Step 2:** Redirect user to the URL. They'll be redirected back with a token.

---

## Collections & Documents

Collections are like tables in a traditional database, but schema-less (NoSQL). Documents are like rows/records.

### Create a Collection

**Endpoint:** `POST /collections/`

```bash
POST https://api.cocobase.buzz/collections/
Content-Type: application/json
x-api-key: YOUR_API_KEY

{
  "name": "posts"
}
```

### Create a Document

**Endpoint:** `POST /collections/documents`

**Simple Document (JSON):**
```bash
POST https://api.cocobase.buzz/collections/documents?collection=posts
Content-Type: application/json
x-api-key: YOUR_API_KEY

{
  "title": "My First Post",
  "content": "Hello World!",
  "author_id": "user-123",
  "tags": ["tutorial", "beginner"],
  "published": true
}
```

**Document with File Uploads:**
```bash
POST https://api.cocobase.buzz/collections/documents?collection=posts
Content-Type: multipart/form-data
x-api-key: YOUR_API_KEY

data: {"title": "Post with Images", "content": "Check out these photos!"}
cover_image: @cover.jpg
gallery: @photo1.jpg
gallery: @photo2.jpg
```

**Response:**
```json
{
  "id": "doc-789",
  "created_at": "2025-01-15T11:00:00",
  "title": "My First Post",
  "content": "Hello World!",
  "author_id": "user-123",
  "tags": ["tutorial", "beginner"],
  "published": true
}
```

### List Documents with Filtering

**Endpoint:** `GET /collections/{collection}/documents`

**Basic Query:**
```bash
GET https://api.cocobase.buzz/collections/posts/documents?limit=20&offset=0
x-api-key: YOUR_API_KEY
```

**Advanced Filtering:**
```bash
# Filter by field value
GET /collections/posts/documents?published=true

# Comparison operators
GET /collections/posts/documents?views_gte=100

# String search
GET /collections/posts/documents?title_contains=tutorial

# Array operations
GET /collections/posts/documents?tags_in=tutorial,beginner

# Multiple conditions (AND)
GET /collections/posts/documents?published=true&category=tech

# OR conditions
GET /collections/posts/documents?[or]category=tech&[or]category=business

# Sort results
GET /collections/posts/documents?sort=created_at&order=desc
```

**Available Operators:**
- `eq` - Equals (default)
- `ne` - Not equals
- `gt`, `gte`, `lt`, `lte` - Comparisons
- `contains` - Substring search (case-insensitive)
- `startswith` - Starts with
- `endswith` - Ends with
- `in` - Value in list (comma-separated)
- `notin` - Value not in list
- `isnull` - Is null/not null

**Response:**
```json
{
  "data": [
    {
      "id": "doc-789",
      "created_at": "2025-01-15T11:00:00",
      "title": "My First Post",
      "published": true
    }
  ],
  "total": 50,
  "limit": 20,
  "offset": 0,
  "has_more": true
}
```

### Populate Relationships

**Endpoint:** `GET /collections/{collection}/documents?populate=field`

```bash
# Populate a single relationship (auto-detect)
GET /collections/posts/documents?populate=author

# Populate multiple relationships
GET /collections/posts/documents?populate=author&populate=category

# Nested population
GET /collections/comments/documents?populate=post.author

# Explicit source type (NEW!)
GET /collections/posts/documents?populate=author:appuser        # From AppUser table
GET /collections/posts/documents?populate=user:members          # From "members" collection
GET /collections/posts/documents?populate=person:people         # From "people" collection
GET /collections/posts/documents?populate=owner:custom_users    # From "custom_users" collection
```

**How Populate Works:**
- Looks for `field_id` or `field_ids` in your document
- Auto-detects if it should fetch from AppUser table or a collection
- Returns the full related object(s) instead of just IDs

**Syntax:**
- `field` → Auto-detect (pluralizes field name, checks if system collection)
- `field:appuser` → Force fetch from AppUser table
- `field:collection_name` → Force fetch from specific collection

**Example 1: Auto-detect**
```json
// Document data
{
  "id": "post-123",
  "title": "Hello World",
  "author_id": "user-456"
}

// Request: ?populate=author
// Auto-pluralizes to "authors" and looks for collection

// Response
{
  "id": "post-123",
  "title": "Hello World",
  "author_id": "user-456",
  "author": {
    "id": "user-456",
    "name": "John Doe",
    "bio": "Writer"
  }
}
```

**Example 2: Specify AppUser**
```json
// Document data
{
  "id": "group-123",
  "name": "Tech Group",
  "owner_id": "appuser-789",
  "member_ids": ["appuser-111", "appuser-222"]
}

// Request: ?populate=owner:appuser&populate=member:appuser
// Forces fetch from AppUser table

// Response
{
  "id": "group-123",
  "name": "Tech Group",
  "owner_id": "appuser-789",
  "member_ids": ["appuser-111", "appuser-222"],
  "owner": {
    "id": "appuser-789",
    "email": "admin@example.com",
    "data": { "username": "admin" }
  },
  "member": [
    {
      "id": "appuser-111",
      "email": "member1@example.com",
      "data": { "username": "member1" }
    },
    {
      "id": "appuser-222",
      "email": "member2@example.com",
      "data": { "username": "member2" }
    }
  ]
}
```

**Example 3: Specify Collection Name**
```json
// Document data
{
  "id": "post-123",
  "title": "My Post",
  "user_id": "custom-user-456"  // NOT an AppUser ID
}

// Request: ?populate=user:custom_users
// Fetches from "custom_users" collection instead of AppUser table

// Response
{
  "id": "post-123",
  "title": "My Post",
  "user_id": "custom-user-456",
  "user": {
    "id": "custom-user-456",
    "display_name": "Custom User",
    "role": "contributor"
  }
}
```

**Example 4: Handling Name Conflicts**
```json
// You have BOTH:
// - AppUser table (for authentication)
// - "users" collection (for custom user profiles)

// Document data
{
  "id": "activity-123",
  "app_user_id": "auth-user-789",    // References AppUser
  "profile_user_id": "profile-456"    // References "users" collection
}

// Request: ?populate=app_user:appuser&populate=profile_user:users

// Response
{
  "id": "activity-123",
  "app_user_id": "auth-user-789",
  "profile_user_id": "profile-456",
  "app_user": {
    "id": "auth-user-789",
    "email": "john@example.com",
    // ... AppUser fields
  },
  "profile_user": {
    "id": "profile-456",
    "bio": "Software developer",
    "avatar": "https://...",
    // ... custom profile fields
  }
}
```

### Get Single Document

**Endpoint:** `GET /collections/{collection}/documents/{document_id}`

```bash
GET https://api.cocobase.buzz/collections/posts/documents/doc-789
x-api-key: YOUR_API_KEY

# With population
GET https://api.cocobase.buzz/collections/posts/documents/doc-789?populate=author
```

### Update Document

**Endpoint:** `PATCH /collections/{collection}/documents/{document_id}`

**Simple Update (Merge):**
```bash
PATCH https://api.cocobase.buzz/collections/posts/documents/doc-789
Content-Type: application/json
x-api-key: YOUR_API_KEY

{
  "title": "Updated Title",
  "updated": true
}
```

**Array Operations (NEW!):**

Managing arrays is now super easy with `$append` and `$remove`:

```bash
# Add items to array
PATCH https://api.cocobase.buzz/collections/group/documents/doc-123
Content-Type: application/json
x-api-key: YOUR_API_KEY

{
  "$append": {
    "member_ids": ["new-member-1", "new-member-2"],
    "tags": ["featured"]
  }
}

# Remove items from array
{
  "$remove": {
    "member_ids": ["old-member-id"],
    "tags": ["draft"]
  }
}

# Combine operations
{
  "title": "Updated Group",
  "$append": {
    "member_ids": ["new-member"]
  },
  "$remove": {
    "member_ids": ["removed-member"]
  }
}
```

**Example:**
```json
// Before:
{
  "name": "Tech Group",
  "member_ids": ["alice", "bob"]
}

// Request:
{
  "$append": {"member_ids": ["charlie"]},
  "$remove": {"member_ids": ["alice"]}
}

// After:
{
  "name": "Tech Group",
  "member_ids": ["bob", "charlie"]
}
```

**Update with File Upload:**
```bash
PATCH https://api.cocobase.buzz/collections/posts/documents/doc-789
Content-Type: multipart/form-data
x-api-key: YOUR_API_KEY

data: {"title": "Updated Post"}
cover_image: @new_cover.jpg
```

### Delete Document

**Endpoint:** `DELETE /collections/{collection}/documents/{document_id}`

```bash
DELETE https://api.cocobase.buzz/collections/posts/documents/doc-789
x-api-key: YOUR_API_KEY
```

### Batch Operations

**Batch Create:**
```bash
POST https://api.cocobase.buzz/collections/posts/batch/documents/create
Content-Type: application/json
x-api-key: YOUR_API_KEY

{
  "documents": [
    {"title": "Post 1", "content": "Content 1"},
    {"title": "Post 2", "content": "Content 2"},
    {"title": "Post 3", "content": "Content 3"}
  ]
}
```

**Batch Update:**
```bash
POST https://api.cocobase.buzz/collections/posts/batch/documents/update
Content-Type: application/json
x-api-key: YOUR_API_KEY

{
  "updates": {
    "doc-1": {"data": {"published": true}},
    "doc-2": {"data": {"published": false}}
  }
}
```

**Batch Delete:**
```bash
POST https://api.cocobase.buzz/collections/posts/batch/documents/delete
Content-Type: application/json
x-api-key: YOUR_API_KEY

{
  "document_ids": ["doc-1", "doc-2", "doc-3"]
}
```

### Advanced Querying

**Count Documents:**
```bash
GET https://api.cocobase.buzz/collections/posts/query/documents/count?published=true
x-api-key: YOUR_API_KEY

# Response: {"count": 42}
```

**Aggregate Data:**
```bash
# Sum
GET /collections/orders/query/documents/aggregate?field=total&operation=sum

# Average
GET /collections/products/query/documents/aggregate?field=price&operation=avg

# Min/Max
GET /collections/products/query/documents/aggregate?field=price&operation=max
```

**Response:**
```json
{
  "field": "total",
  "operation": "sum",
  "result": 15420.50,
  "collection": "orders"
}
```

**Group By:**
```bash
GET /collections/users/query/documents/group-by?field=country
x-api-key: YOUR_API_KEY
```

**Response:**
```json
[
  {"country": "US", "count": 150},
  {"country": "UK", "count": 80},
  {"country": "CA", "count": 45}
]
```

**Get Schema:**
```bash
GET /collections/posts/query/schema
x-api-key: YOUR_API_KEY
```

**Response:**
```json
{
  "collection": "posts",
  "document_count": 100,
  "fields": {
    "title": {
      "types": ["str"],
      "primary_type": "str",
      "nullable": false,
      "samples": ["My First Post", "Tutorial"]
    },
    "views": {
      "types": ["int"],
      "primary_type": "int",
      "nullable": true,
      "samples": [100, 250, 500]
    }
  },
  "detected_relationships": {
    "author_id": {
      "type": "belongs_to",
      "target_collection": "authors",
      "confidence": "high"
    }
  }
}
```

**Export Collection:**
```bash
# Export as JSON
GET /collections/posts/export?format=json

# Export as CSV
GET /collections/posts/export?format=csv

# Export with filters
GET /collections/posts/export?format=json&published=true&category=tech
```

---

## File Storage

### Upload File

**Endpoint:** `POST /collections/file`

```bash
POST https://api.cocobase.buzz/collections/file
Content-Type: multipart/form-data
x-api-key: YOUR_API_KEY

file: @document.pdf
directory: documents
```

**Response:**
```json
{
  "status": "success",
  "url": "https://f005.backblazeb2.com/file/cocobase/project-123/documents/document.pdf",
  "filename": "document.pdf",
  "size": 102400
}
```

**Storage Limits:**
- **Free:** 100 MB
- **Starter:** 1 GB
- **Pro:** 10 GB
- **Enterprise:** 100 GB

---

## Real-time Features

### WebSocket - Live Collection Updates

**Endpoint:** `WS /realtime/collections/{collection_id}`

**JavaScript Example:**
```javascript
const ws = new WebSocket(
  'wss://api.cocobase.buzz/realtime/collections/posts?api_key=YOUR_API_KEY'
);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.event === 'CREATE') {
    console.log('New document:', data.document);
  } else if (data.event === 'UPDATE') {
    console.log('Updated document:', data.document);
    console.log('Old data:', data.old_data);
  } else if (data.event === 'DELETE') {
    console.log('Deleted document ID:', data.document_id);
  }
};
```

**Event Types:**
- `CREATE` - New document added
- `UPDATE` - Document modified
- `DELETE` - Document removed

### Webhooks

Configure a webhook URL on your collection to receive HTTP callbacks when documents change:

```bash
PATCH https://api.cocobase.buzz/collections/posts
Content-Type: application/json
x-api-key: YOUR_API_KEY

{
  "webhook_url": "https://your-app.com/webhook"
}
```

**Webhook Payload:**
```json
{
  "event_type": "CREATE",
  "document_id": "doc-123",
  "data": {
    "title": "New Post",
    "content": "Content here"
  },
  "created_at": "2025-01-15T12:00:00"
}
```

### Dynamic Webhook URLs (Coco Hooks)

Generate temporary webhook URLs for testing:

```bash
GET https://api.cocobase.buzz/coco-hooks/new-url
```

**Response:**
```json
{
  "webhook_url": "https://api.cocobase.buzz/coco-hooks/abc-123-def",
  "stream_url": "https://api.cocobase.buzz/coco-hooks/stream/abc-123-def"
}
```

**Stream Events (SSE):**
```javascript
const eventSource = new EventSource(
  'https://api.cocobase.buzz/coco-hooks/stream/abc-123-def'
);

eventSource.onmessage = (event) => {
  const payload = JSON.parse(event.data);
  console.log('Received webhook:', payload);
};
```

---

## Advanced Features

### Permissions & Access Control

Set collection-level permissions:

```bash
POST https://api.cocobase.buzz/project/{project_id}/collections/{collection_id}/permissions
Content-Type: application/json
x-api-key: YOUR_API_KEY

{
  "read": ["user", "admin"],
  "create": ["admin"],
  "update": ["admin"],
  "delete": ["admin"]
}
```

### Analytics

**Project Overview:**
```bash
GET https://api.cocobase.buzz/analytics/{project_id}/overview
x-api-key: YOUR_API_KEY
```

**Response:**
```json
{
  "total_users": 1250,
  "total_collections": 8,
  "total_documents": 5420,
  "storage_used_mb": 450,
  "api_calls_today": 3200
}
```

**User Activity:**
```bash
GET https://api.cocobase.buzz/analytics/{project_id}/users/activity
```

**Collection Stats:**
```bash
GET https://api.cocobase.buzz/analytics/{project_id}/collections/{collection_id}/stats
```

### Data Import/Migration

Import data from external databases:

```bash
POST https://api.cocobase.buzz/import/introspect-database
Content-Type: application/json
x-api-key: YOUR_API_KEY

{
  "connection_string": "postgresql://user:pass@host:5432/db",
  "database_type": "postgresql"
}
```

**Supported Databases:**
- PostgreSQL
- MySQL
- MongoDB
- SQLite

**Start Migration:**
```bash
POST https://api.cocobase.buzz/import/migrate-data
Content-Type: application/json
x-api-key: YOUR_API_KEY

{
  "connection_string": "postgresql://...",
  "database_type": "postgresql",
  "tables": ["users", "posts", "comments"],
  "batch_size": 100
}
```

### AI Assistant

Ask questions about your data or generate code:

```bash
POST https://api.cocobase.buzz/ai-assistant/{project_id}/ask
Content-Type: application/json
Authorization: Bearer YOUR_USER_TOKEN

{
  "message": "How do I create a new collection?"
}
```

**Response:**
```json
{
  "response": "To create a new collection, send a POST request to...",
  "conversation_id": "conv-123"
}
```

**Generate Code:**
```bash
POST https://api.cocobase.buzz/ai-assistant/{project_id}/generate-code
Content-Type: application/json
Authorization: Bearer YOUR_USER_TOKEN

{
  "task": "Create a React component that fetches posts from my 'posts' collection"
}
```

---

## ORM Features & Recommendations

### Current AppUser Model Features

Your `AppUser` model currently has:

✅ **Core Fields:**
- `id` - UUID primary key
- `email` - User email (unique per project)
- `password` - Hashed password
- `client_id` - Multi-tenancy (project isolation)
- `data` - JSONB field for flexible custom data
- `created_at` - Timestamp
- `oauth_id` - OAuth integration support
- `roles` - Array of role strings

✅ **Advanced Features:**
- Unique constraint on (client_id, email)
- GIN index on JSONB data for fast queries
- Password hashing/verification methods
- OAuth support

### Recommended Additional Fields

Consider adding these commonly-used features:

**1. Email Verification:**
```python
email_verified = Column(Boolean, default=False)
email_verified_at = Column(DateTime, nullable=True)
```

**2. Activity Tracking:**
```python
last_login_at = Column(DateTime, nullable=True)
last_active_at = Column(DateTime, nullable=True)
updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

**3. Account Status:**
```python
is_active = Column(Boolean, default=True)
is_suspended = Column(Boolean, default=False)
suspended_reason = Column(String, nullable=True)
```

**4. Soft Deletes:**
```python
deleted_at = Column(DateTime, nullable=True)
is_deleted = Column(Boolean, default=False)
```

**5. Profile Fields** (Optional - can use JSONB `data` instead):
```python
username = Column(String, nullable=True)
first_name = Column(String, nullable=True)
last_name = Column(String, nullable=True)
avatar_url = Column(String, nullable=True)
```

**6. Password Reset:**
```python
password_reset_token = Column(String, nullable=True)
password_reset_expires_at = Column(DateTime, nullable=True)
```

**7. Multi-Factor Authentication:**
```python
mfa_enabled = Column(Boolean, default=False)
mfa_secret = Column(String, nullable=True)
```

### Why JSONB `data` Field is Powerful

Instead of adding schema fields, you can store custom data in the `data` JSONB column:

```json
{
  "id": "user-123",
  "email": "john@example.com",
  "data": {
    "username": "johndoe",
    "first_name": "John",
    "last_name": "Doe",
    "avatar_url": "https://...",
    "bio": "Software developer",
    "preferences": {
      "theme": "dark",
      "notifications": true
    },
    "social_links": {
      "twitter": "@johndoe",
      "github": "johndoe"
    }
  }
}
```

**Benefits:**
- No schema migrations needed
- Flexible per-project data structure
- Fast GIN-indexed queries
- Perfect for custom fields

---

## Missing Features & Roadmap

### ✅ Currently Implemented

- [x] Collections & Documents (NoSQL)
- [x] User Authentication (JWT, OAuth)
- [x] File Storage (Backblaze B2)
- [x] Real-time Updates (WebSockets)
- [x] Webhooks (Dynamic & Static)
- [x] Batch Operations
- [x] Advanced Filtering & Querying
- [x] Relationships & Population
- [x] Array Operations ($append, $remove)
- [x] Analytics & Reporting
- [x] Data Import/Migration
- [x] AI Assistant
- [x] Permissions & Access Control
- [x] Payments & Subscriptions
- [x] Team Collaboration
- [x] Cron Jobs

### 🚧 Partially Implemented

- [ ] **Email Services** - Framework exists, needs:
  - Email templates
  - SMTP configuration UI
  - Email verification flow
  - Password reset emails

- [ ] **Cloud Functions** - Model defined, needs:
  - Code execution engine
  - Deployment system
  - Logging & monitoring

- [ ] **Push Notifications** - Needs:
  - FCM integration
  - APNS integration
  - Device token management
  - Notification scheduling

### 📋 Missing/Recommended Features

**1. GraphQL API**
- Alternative to REST
- Single endpoint for complex queries
- Real-time subscriptions

**2. Server-Side Rendering (SSR)**
- Pre-render pages for SEO
- Faster initial page loads

**3. CDN Integration**
- Edge caching for static files
- Global content delivery

**4. Database Backups**
- Automated daily backups
- Point-in-time recovery
- Backup management UI

**5. Rate Limiting Enhancements**
- Per-user rate limits
- Per-endpoint customization
- DDoS protection

**6. Advanced Search**
- Full-text search with PostgreSQL
- Elasticsearch integration
- Fuzzy matching
- Search suggestions

**7. Geo-location Features**
- Location-based queries
- Distance calculations
- Geo-fencing

**8. Image Processing**
- Auto-resize on upload
- Thumbnail generation
- Format conversion
- Optimization

**9. Video Processing**
- Transcoding
- Thumbnail extraction
- Streaming support

**10. Audit Logs**
- Track all data changes
- User activity logs
- Admin action logs
- Compliance reports

**11. Multi-language Support (i18n)**
- Content translation
- Locale management
- Auto-translation

**12. A/B Testing**
- Feature flags
- Experiment tracking
- Analytics integration

**13. Scheduled Tasks (Enhanced)**
- User-defined cron jobs
- Recurring tasks
- Task history

**14. Database Transactions**
- Atomic operations
- Rollback support
- ACID compliance

**15. API Versioning**
- Version management
- Deprecation notices
- Migration guides

**16. SDK Generation**
- Auto-generate client libraries
- TypeScript, Python, Go, etc.
- OpenAPI/Swagger support

**17. Monitoring & Alerting**
- Uptime monitoring
- Error tracking (Sentry integration)
- Performance metrics
- Alert rules

**18. Cache Management**
- Redis caching layer
- Cache invalidation
- Cache warming
- Query result caching

**19. File Versioning**
- Track file changes
- Restore previous versions
- Version history

**20. Collaboration Features**
- Comments on documents
- Mentions & notifications
- Activity feeds
- Real-time editing (CRDT)

**21. Data Validation**
- Schema validation
- Custom validators
- Client-side validation generation

**22. Workflow Automation**
- Visual workflow builder
- Triggers & actions
- Zapier-like integrations

**23. Dashboard Builder**
- Drag-and-drop UI
- Custom widgets
- Data visualization
- Public dashboards

**24. API Documentation**
- Auto-generated docs
- Interactive API explorer
- Code examples
- Postman collections

**25. Database Indexing UI**
- Visual index management
- Index recommendations
- Query performance analysis

---

## Performance Best Practices

### 1. Use Pagination
Always use `limit` and `offset` for large datasets:

```bash
GET /collections/posts/documents?limit=50&offset=0
```

### 2. Use Indexes
Common query fields should be indexed (done automatically for `email`, `created_at`).

### 3. Optimize Queries
- Use specific filters instead of fetching all and filtering client-side
- Use `count=false` to skip counting when not needed
- Use projection (`select`) to fetch only needed fields

### 4. Cache Responses
- Use ETags for conditional requests
- Cache static content
- Use Redis for frequently accessed data

### 5. Batch Operations
Use batch endpoints when creating/updating multiple documents:

```bash
POST /collections/posts/batch/documents/create
```

### 6. WebSocket vs Polling
Use WebSockets for real-time updates instead of polling:

```javascript
// Good ✅
const ws = new WebSocket('wss://api.cocobase.buzz/realtime/collections/posts');

// Bad ❌
setInterval(() => fetch('/collections/posts/documents'), 1000);
```

---

## Error Handling

### Common Error Codes

| Code | Meaning | Solution |
|------|---------|----------|
| 400 | Bad Request | Check request body format |
| 401 | Unauthorized | Verify API key or auth token |
| 403 | Forbidden | Check user permissions |
| 404 | Not Found | Verify resource ID |
| 429 | Rate Limited | Slow down requests |
| 500 | Server Error | Contact support |

### Error Response Format

```json
{
  "detail": "Error message here"
}
```

---

## Rate Limits

| Plan | API Calls/Hour | Users | Storage |
|------|---------------|-------|---------|
| **Free** | 1,000 | 100 | 100 MB |
| **Starter** | 10,000 | 1,000 | 1 GB |
| **Pro** | 100,000 | 10,000 | 10 GB |
| **Enterprise** | Unlimited | Unlimited | 100 GB |

---

## Support & Resources

- **Documentation:** https://docs.cocobase.buzz
- **API Reference:** https://api.cocobase.buzz/docs
- **GitHub:** https://github.com/cocobase
- **Discord Community:** https://discord.gg/cocobase
- **Email Support:** support@cocobase.buzz

---

## Quick Reference

### Authentication Headers

```bash
# User Authentication
Authorization: Bearer YOUR_USER_TOKEN

# Project API Key
x-api-key: YOUR_PROJECT_API_KEY

# App User Authentication
Authorization: Bearer APP_USER_TOKEN
```

### Common Endpoints

```bash
# Auth
POST   /auth-collections/signup
POST   /auth-collections/login
GET    /auth-collections/user

# Collections
POST   /collections/documents?collection=NAME
GET    /collections/NAME/documents
GET    /collections/NAME/documents/{id}
PATCH  /collections/NAME/documents/{id}
DELETE /collections/NAME/documents/{id}

# Files
POST   /collections/file

# Real-time
WS     /realtime/collections/{collection_id}
```

---

**Built with ❤️ using FastAPI, PostgreSQL, and Redis**
