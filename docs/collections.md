# Collections API

Store and manage JSON documents in collections (like tables in a database).

**Base URL:** `https://api.cocobase.buzz/collections`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Create Document](#create-document)
3. [Get All Documents](#get-all-documents)
4. [Get Single Document](#get-single-document)
5. [Update Document](#update-document)
6. [Delete Document](#delete-document)
7. [Batch Operations](#batch-operations)
8. [Advanced Queries](#advanced-queries)

---

## Authentication

Include your API key in all requests:

```bash
X-API-Key: your-api-key-here
```

---

## Create Document

Add a new document to a collection.

**Endpoint:** `POST /collections/{collection_name}/documents`

**Example:**
```bash
curl -X POST https://api.cocobase.buzz/collections/users/documents \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "age": 25,
    "status": "active",
    "role": "user"
  }'
```

**Response:**
```json
{
  "id": "doc_abc123xyz",
  "name": "John Doe",
  "email": "john@example.com",
  "age": 25,
  "status": "active",
  "role": "user",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Notes:**
- Collections are created automatically on first document insert
- Document IDs are auto-generated
- `created_at` timestamp is added automatically
- You can store any valid JSON structure

---

## Get All Documents

Retrieve documents from a collection with filtering, sorting, and pagination.

**Endpoint:** `GET /collections/{collection_name}/documents`

### Basic Query

```bash
curl https://api.cocobase.buzz/collections/users/documents \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "data": [
    {
      "id": "doc_abc123",
      "name": "John Doe",
      "email": "john@example.com",
      "age": 25,
      "status": "active",
      "created_at": "2024-01-15T10:30:00Z"
    },
    {
      "id": "doc_def456",
      "name": "Jane Smith",
      "email": "jane@example.com",
      "age": 30,
      "status": "active",
      "created_at": "2024-01-15T11:00:00Z"
    }
  ],
  "total": 2,
  "limit": 10,
  "offset": 0,
  "has_more": false
}
```

### With Filters

```bash
# Active users only
curl "https://api.cocobase.buzz/collections/users/documents?status=active" \
  -H "X-API-Key: your-api-key"

# Users over 18
curl "https://api.cocobase.buzz/collections/users/documents?age_gte=18" \
  -H "X-API-Key: your-api-key"

# Search by name
curl "https://api.cocobase.buzz/collections/users/documents?name_contains=john" \
  -H "X-API-Key: your-api-key"

# Multiple conditions (AND)
curl "https://api.cocobase.buzz/collections/users/documents?status=active&age_gte=18&age_lte=65" \
  -H "X-API-Key: your-api-key"
```

### Filter Operators

| Operator | Description | Example | Matches |
|----------|-------------|---------|---------|
| `field` | Exact match | `status=active` | `{"status": "active"}` |
| `field_eq` | Exact match (explicit) | `status_eq=active` | `{"status": "active"}` |
| `field_ne` | Not equal | `status_ne=inactive` | `{"status": "active"}` |
| `field_gt` | Greater than | `age_gt=18` | `{"age": 19}` |
| `field_gte` | Greater than or equal | `age_gte=18` | `{"age": 18}` |
| `field_lt` | Less than | `age_lt=65` | `{"age": 64}` |
| `field_lte` | Less than or equal | `age_lte=65` | `{"age": 65}` |
| `field_contains` | Contains substring | `name_contains=john` | `{"name": "John Doe"}` |
| `field_startswith` | Starts with | `email_startswith=admin` | `{"email": "admin@..."}` |
| `field_endswith` | Ends with | `email_endswith=@gmail.com` | `{"email": "...@gmail.com"}` |
| `field_in` | In list | `role_in=admin,moderator` | `{"role": "admin"}` |
| `field_notin` | Not in list | `status_notin=deleted,archived` | `{"status": "active"}` |
| `field_isnull` | Is null | `deleted_at_isnull=true` | `{"deleted_at": null}` |

**Note:** All string comparisons are case-insensitive.

### OR Conditions

```bash
# Users who are EITHER over 65 OR have admin role
curl "https://api.cocobase.buzz/collections/users/documents?[or]age_gte=65&[or]role=admin" \
  -H "X-API-Key: your-api-key"

# Search in multiple fields
curl "https://api.cocobase.buzz/collections/users/documents?name__or__email_contains=john" \
  -H "X-API-Key: your-api-key"
```

### Sorting

```bash
# Sort by age, descending
curl "https://api.cocobase.buzz/collections/users/documents?sort=age&order=desc" \
  -H "X-API-Key: your-api-key"

# Sort by created_at, ascending
curl "https://api.cocobase.buzz/collections/users/documents?sort=created_at&order=asc" \
  -H "X-API-Key: your-api-key"
```

**Sort Fields:**
- Any document field (e.g., `name`, `age`, `email`)
- `created_at` (document creation time)
- `id` (document ID)

**Order:**
- `asc` - Ascending (default)
- `desc` - Descending

### Pagination

```bash
# Get first 20 documents
curl "https://api.cocobase.buzz/collections/users/documents?limit=20&offset=0" \
  -H "X-API-Key: your-api-key"

# Get next 20 documents
curl "https://api.cocobase.buzz/collections/users/documents?limit=20&offset=20" \
  -H "X-API-Key: your-api-key"
```

**Parameters:**
- `limit` - Number of documents to return (default: 10, max: 100)
- `offset` - Number of documents to skip (default: 0)

---

## Get Single Document

Retrieve a specific document by ID.

**Endpoint:** `GET /collections/{collection_name}/documents/{document_id}`

**Example:**
```bash
curl https://api.cocobase.buzz/collections/users/documents/doc_abc123 \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "id": "doc_abc123",
  "name": "John Doe",
  "email": "john@example.com",
  "age": 25,
  "status": "active",
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Error Response (404):**
```json
{
  "detail": "Document not found"
}
```

---

## Update Document

Update an existing document (partial or full update).

**Endpoint:** `PATCH /collections/{collection_name}/documents/{document_id}`

### Basic Update

**Example:**
```bash
curl -X PATCH https://api.cocobase.buzz/collections/users/documents/doc_abc123 \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 26,
    "status": "premium"
  }'
```

**Response:**
```json
{
  "id": "doc_abc123",
  "name": "John Doe",
  "email": "john@example.com",
  "age": 26,
  "status": "premium",
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Array Operations (NEW!)

Manage array fields (like likes, followers, tags) without replacing the entire array.

#### Append to Array

Add items to an array field. Creates the array if it doesn't exist. Prevents duplicates automatically.

```bash
curl -X PATCH https://api.cocobase.buzz/collections/posts/documents/post_123 \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "$append": {
      "likes": ["user_456"],
      "tags": ["featured"]
    }
  }'
```

**Before:**
```json
{
  "id": "post_123",
  "title": "My Post",
  "likes": ["user_123"]
}
```

**After:**
```json
{
  "id": "post_123",
  "title": "My Post",
  "likes": ["user_123", "user_456"],
  "tags": ["featured"]
}
```

#### Remove from Array

Remove specific items from an array field.

```bash
curl -X PATCH https://api.cocobase.buzz/collections/posts/documents/post_123 \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "$remove": {
      "likes": ["user_123"]
    }
  }'
```

**Result:**
```json
{
  "id": "post_123",
  "title": "My Post",
  "likes": ["user_456"]
}
```

#### Combined Operations

Update regular fields and manage arrays in one request:

```bash
curl -X PATCH https://api.cocobase.buzz/collections/posts/documents/post_123 \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Updated Title",
    "views": 150,
    "$append": {
      "likes": ["user_789"]
    },
    "$remove": {
      "likes": ["user_123"]
    }
  }'
```

**JavaScript Example - Toggle Like:**
```javascript
// Like a post
await fetch(`https://api.cocobase.buzz/collections/posts/documents/post_123`, {
  method: 'PATCH',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    $append: {
      likes: ['user_456']
    }
  })
});

// Unlike a post
await fetch(`https://api.cocobase.buzz/collections/posts/documents/post_123`, {
  method: 'PATCH',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    $remove: {
      likes: ['user_456']
    }
  })
});
```

**Notes:**
- Only specified fields are updated (partial update)
- Existing fields not mentioned remain unchanged
- Document ID and `created_at` cannot be changed
- `$append` creates arrays automatically if they don't exist
- `$append` prevents duplicate entries
- `$remove` safely handles missing fields
- Operations execute in order: remove → append → regular updates

---

## Delete Document

Permanently delete a document.

**Endpoint:** `DELETE /collections/{collection_name}/documents/{document_id}`

**Example:**
```bash
curl -X DELETE https://api.cocobase.buzz/collections/users/documents/doc_abc123 \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "status": "success",
  "message": "Document deleted successfully"
}
```

**Error Response (404):**
```json
{
  "detail": "Document not found"
}
```

---

## Batch Operations

Perform operations on multiple documents at once.

### Batch Create

Create multiple documents in one request.

**Endpoint:** `POST /collections/{collection_name}/batch/documents`

**Example:**
```bash
curl -X POST https://api.cocobase.buzz/collections/users/batch/documents \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {"name": "Alice Johnson", "email": "alice@example.com", "age": 28},
      {"name": "Bob Wilson", "email": "bob@example.com", "age": 35},
      {"name": "Charlie Brown", "email": "charlie@example.com", "age": 42}
    ]
  }'
```

**Response:**
```json
[
  {
    "id": "doc_abc123",
    "name": "Alice Johnson",
    "email": "alice@example.com",
    "age": 28,
    "created_at": "2024-01-15T12:00:00Z"
  },
  {
    "id": "doc_def456",
    "name": "Bob Wilson",
    "email": "bob@example.com",
    "age": 35,
    "created_at": "2024-01-15T12:00:01Z"
  },
  {
    "id": "doc_ghi789",
    "name": "Charlie Brown",
    "email": "charlie@example.com",
    "age": 42,
    "created_at": "2024-01-15T12:00:02Z"
  }
]
```

### Batch Update

Update multiple documents in one request.

**Endpoint:** `POST /collections/{collection_name}/batch/documents/update`

#### Basic Batch Update

```bash
curl -X POST https://api.cocobase.buzz/collections/users/batch/documents/update \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "updates": {
      "doc_abc123": {
        "data": {"status": "premium", "plan": "pro"}
      },
      "doc_def456": {
        "data": {"status": "active", "verified": true}
      }
    }
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "Updated 2 documents",
  "count": 2
}
```

#### Batch Update with Array Operations (NEW!)

Update multiple documents with array operations in a single request:

```bash
curl -X POST https://api.cocobase.buzz/collections/posts/batch/documents/update \
  -H "X-API-Key": your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "updates": {
      "post_123": {
        "data": {"views": 200},
        "$append": {"likes": ["user_999"]},
        "$remove": {"likes": ["user_111"]}
      },
      "post_456": {
        "$append": {"likes": ["user_999"], "tags": ["trending"]}
      },
      "post_789": {
        "data": {"status": "published"}
      }
    }
  }'
```

**JavaScript Example - Batch Like Multiple Posts:**
```javascript
await fetch('https://api.cocobase.buzz/collections/posts/batch/documents/update', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    updates: {
      'post_123': {
        $append: { likes: ['user_456'] }
      },
      'post_456': {
        $append: { likes: ['user_456'] }
      },
      'post_789': {
        $append: { likes: ['user_456'] }
      }
    }
  })
});
```

**Use Cases:**
- Like/unlike multiple posts at once
- Add tags to multiple documents
- Manage permissions across multiple resources
- Bulk update member lists

### Batch Delete

Delete multiple documents in one request.

**Endpoint:** `POST /collections/{collection_name}/batch/documents/delete`

**Example:**
```bash
curl -X POST https://api.cocobase.buzz/collections/users/batch/documents/delete \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "document_ids": ["doc_abc123", "doc_def456", "doc_ghi789"]
  }'
```

**Response:**
```json
{
  "status": "success",
  "message": "Deleted 3 documents",
  "count": 3
}
```

---

## Advanced Queries

### Complex OR Groups

Combine multiple OR conditions:

```bash
# (age >= 65 OR status = 'vip') AND role = 'user'
curl "https://api.cocobase.buzz/collections/users/documents?[or]age_gte=65&[or]status=vip&role=user" \
  -H "X-API-Key: your-api-key"
```

### Named OR Groups

Create multiple independent OR groups:

```bash
# (age >= 18 AND age <= 25) OR (age >= 60 AND age <= 70)
curl "https://api.cocobase.buzz/collections/users/documents?[or:young]age_gte=18&[or:young]age_lte=25&[or:senior]age_gte=60&[or:senior]age_lte=70" \
  -H "X-API-Key: your-api-key"
```

### Field Selection

Select specific fields only:

```bash
curl "https://api.cocobase.buzz/collections/users/documents?select=name,email" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "data": [
    {
      "id": "doc_abc123",
      "name": "John Doe",
      "email": "john@example.com"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0
}
```

### Count Without Data

Get total count without fetching documents:

```bash
curl "https://api.cocobase.buzz/collections/users/documents?count=true&limit=0" \
  -H "X-API-Key: your-api-key"
```

---

## JavaScript Examples

### Fetch Documents

```javascript
const response = await fetch('https://api.cocobase.buzz/collections/users/documents?status=active', {
  headers: {
    'X-API-Key': 'your-api-key'
  }
});

const result = await response.json();
console.log(result.data); // Array of documents
```

### Create Document

```javascript
const response = await fetch('https://api.cocobase.buzz/collections/users/documents', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'John Doe',
    email: 'john@example.com',
    age: 25
  })
});

const document = await response.json();
console.log(document.id); // doc_abc123
```

### Update Document

```javascript
const response = await fetch('https://api.cocobase.buzz/collections/users/documents/doc_abc123', {
  method: 'PUT',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    age: 26,
    status: 'premium'
  })
});

const updated = await response.json();
```

### Delete Document

```javascript
const response = await fetch('https://api.cocobase.buzz/collections/users/documents/doc_abc123', {
  method: 'DELETE',
  headers: {
    'X-API-Key': 'your-api-key'
  }
});

const result = await response.json();
console.log(result.message); // Document deleted successfully
```

---

## Python Examples

```python
import requests

API_KEY = 'your-api-key'
BASE_URL = 'https://api.cocobase.buzz'
headers = {'X-API-Key': API_KEY}

# Create document
response = requests.post(
    f'{BASE_URL}/collections/users/documents',
    headers=headers,
    json={
        'name': 'John Doe',
        'email': 'john@example.com',
        'age': 25
    }
)
document = response.json()

# Query documents
response = requests.get(
    f'{BASE_URL}/collections/users/documents',
    headers=headers,
    params={'status': 'active', 'age_gte': 18}
)
result = response.json()

# Update document
response = requests.put(
    f'{BASE_URL}/collections/users/documents/{document["id"]}',
    headers=headers,
    json={'age': 26}
)

# Delete document
response = requests.delete(
    f'{BASE_URL}/collections/users/documents/{document["id"]}',
    headers=headers
)
```

---

## Best Practices

### 1. Use Specific Filters
```bash
# ✅ Good: Specific query
?status=active&role=user&age_gte=18

# ❌ Bad: Fetch all and filter client-side
# This wastes bandwidth
```

### 2. Paginate Large Results
```bash
# ✅ Good: Use pagination
?limit=50&offset=0

# ❌ Bad: Fetch everything at once
# This may timeout or consume too much memory
```

### 3. Use Batch Operations
```bash
# ✅ Good: Batch create
POST /batch/documents with 100 documents

# ❌ Bad: Loop and create one by one
# This makes 100 separate requests
```

### 4. Index Your Queries
If you frequently query by specific fields, contact support to add indexes for better performance.

---

## Rate Limits

- **Reads:** 1000 requests/minute
- **Writes:** 500 requests/minute
- **Batch operations:** 100 requests/minute

See [Rate Limits](./rate-limits.md) for details.

---

## Next Steps

- **[Auth Collections](./auth-collections.md)** - Add user authentication
- **[Filtering Guide](./filtering.md)** - Advanced filtering techniques
- **[Realtime](./realtime/overview.md)** - Watch collections in real-time
- **[Relationships](./relationships.md)** - Link documents together

---

**Need Help?** Contact support@cocobase.com
