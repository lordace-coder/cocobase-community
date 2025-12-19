# ORM API Keys Implementation

## Overview

Successfully implemented ORM API Keys functionality for the CocoBase project. This allows users to generate secure API keys for project-scoped database access.

## Key Format

```
coco_orm_<project_id>_<random_32_chars>
```

**Example:**
```
coco_orm_901235c6-9564-4de0-bb40_8a7f3e9d2c1b4f6a8e5d7c9b3a1f2e4d
```

## Files Created

### 1. Database Model
**File:** [app/models/orm_api_keys.py](app/models/orm_api_keys.py)

- `ORMApiKey` model with the following fields:
  - `id` - Unique identifier
  - `project_id` - Foreign key to projects table
  - `key_hash` - bcrypt hash of the API key
  - `key_prefix` - First 16 characters for display
  - `name` - User-defined name for the key
  - `permissions` - JSON object with granular permissions
  - `created_at` - Timestamp when key was created
  - `last_used_at` - Last time the key was used (nullable)
  - `expires_at` - Expiration date (nullable)
  - `is_active` - Active/deactivated status
  - `created_by` - Foreign key to users table
  - `rate_limit` - Requests per minute (nullable, null = plan default)

### 2. Pydantic Schemas
**File:** [app/schemas/orm_api_keys.py](app/schemas/orm_api_keys.py)

- `ORMApiKeyCreate` - Schema for creating new keys
- `ORMApiKeyResponse` - Schema for key metadata (without the actual key)
- `ORMApiKeyCreateResponse` - Schema for creation response (includes full key, shown only once)
- `ORMApiKeyUpdate` - Schema for updating key metadata

### 3. API Routes
**File:** [app/api/orm_api_keys.py](app/api/orm_api_keys.py)

Base path: `/project/{project_id}/orm-keys`

#### Endpoints:

1. **POST /** - Create new ORM API key
   - Returns the full key (only shown once!)
   - Optional expiration date
   - Customizable permissions

2. **GET /** - List all ORM API keys for a project
   - Query param: `active_only` (bool) to filter active keys
   - Returns metadata only (no actual key values)

3. **GET /{key_id}** - Get specific ORM API key details
   - Returns metadata only

4. **PATCH /{key_id}** - Update ORM API key
   - Can update: name, permissions, is_active, rate_limit

5. **DELETE /{key_id}** - Delete ORM API key
   - Permanent deletion

6. **POST /{key_id}/deactivate** - Deactivate key
   - Temporarily revoke access without deletion

7. **POST /{key_id}/activate** - Reactivate key
   - Restore access to deactivated key
   - Validates expiration date

### 4. Utility Function
**File:** [app/services/utils.py](app/services/utils.py)

- `generate_orm_api_key(project_id: str) -> str` - Generates API key with proper format

### 5. Database Migration
**File:** [app/migrations/versions/d58bfa43b928_add_orm_api_keys_table.py](app/migrations/versions/d58bfa43b928_add_orm_api_keys_table.py)

- Creates `orm_api_keys` table
- Creates indexes:
  - `idx_orm_keys_project` on `project_id`
  - `idx_orm_keys_prefix` on `key_prefix`
  - `idx_orm_keys_active` on `is_active, project_id`
- Foreign key constraints with CASCADE delete

### 6. Main App Registration
**File:** [app/main.py](app/main.py)

- Routes registered in both main app and dashboard app

## Database Schema

```sql
CREATE TABLE orm_api_keys (
    id VARCHAR PRIMARY KEY,
    project_id VARCHAR NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    key_hash VARCHAR NOT NULL,
    key_prefix VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    permissions JSON NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_by VARCHAR NOT NULL REFERENCES users(id),
    rate_limit INTEGER
);

CREATE INDEX idx_orm_keys_project ON orm_api_keys(project_id);
CREATE INDEX idx_orm_keys_prefix ON orm_api_keys(key_prefix);
CREATE INDEX idx_orm_keys_active ON orm_api_keys(is_active, project_id);
```

## Permissions Structure

Default permissions:
```json
{
  "collections": {
    "*": ["read"]
  },
  "admin": false,
  "auth": {
    "manage_users": false,
    "manage_roles": false
  }
}
```

Example with full permissions:
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

## API Usage Examples

### Create ORM API Key

```bash
POST /project/{project_id}/orm-keys
Authorization: Bearer {your_auth_token}
Content-Type: application/json

{
  "name": "Production API Key",
  "permissions": {
    "collections": {
      "*": ["read"],
      "users": ["read", "write"]
    },
    "admin": false,
    "auth": {
      "manage_users": true,
      "manage_roles": false
    }
  },
  "expires_in_days": 90,
  "rate_limit": 1000
}
```

**Response:**
```json
{
  "id": "key-uuid",
  "project_id": "proj-uuid",
  "name": "Production API Key",
  "key": "coco_orm_901235c6-9564-4de0-bb40_8a7f3e9d2c1b4f6a8e5d7c9b3a1f2e4d",
  "key_prefix": "coco_orm_901235c6",
  "permissions": {...},
  "created_at": "2025-12-19T10:30:00Z",
  "expires_at": "2026-03-19T10:30:00Z",
  "is_active": true,
  "rate_limit": 1000
}
```

### List ORM API Keys

```bash
GET /project/{project_id}/orm-keys?active_only=true
Authorization: Bearer {your_auth_token}
```

**Response:**
```json
[
  {
    "id": "key-uuid",
    "project_id": "proj-uuid",
    "name": "Production API Key",
    "key_prefix": "coco_orm_901235c6",
    "permissions": {...},
    "created_at": "2025-12-19T10:30:00Z",
    "last_used_at": null,
    "expires_at": "2026-03-19T10:30:00Z",
    "is_active": true,
    "created_by": "user-uuid",
    "rate_limit": 1000
  }
]
```

### Delete ORM API Key

```bash
DELETE /project/{project_id}/orm-keys/{key_id}
Authorization: Bearer {your_auth_token}
```

**Response:**
```json
{
  "message": "ORM API key deleted successfully"
}
```

## Security Features

1. **Key Hashing**: API keys are hashed using bcrypt before storage
2. **Key Prefix**: Only first 16 characters stored for display purposes
3. **One-time Display**: Full key shown only during creation
4. **Cascade Delete**: Keys automatically deleted when project is deleted
5. **User Tracking**: Tracks which user created each key
6. **Expiration**: Optional expiration dates for keys
7. **Activation Toggle**: Keys can be deactivated without deletion
8. **Rate Limiting**: Per-key rate limits can be set

## Next Steps

To use these ORM API keys in the actual ORM microservice:

1. Implement key validation middleware
2. Add rate limiting based on `rate_limit` field
3. Enforce permissions from the `permissions` JSON
4. Update `last_used_at` timestamp on each successful request
5. Check `is_active` and `expires_at` before allowing access

## Migration Status

✅ Migration completed successfully
- Table: `orm_api_keys` created
- Indexes created
- Foreign keys established

To run the migration:
```bash
alembic upgrade head
```

To rollback:
```bash
alembic downgrade -1
```

---

**Implementation Date:** 2025-12-19
**Status:** Complete and Ready for Use
