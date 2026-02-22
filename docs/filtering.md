# Filtering Guide

Complete guide to filtering and querying in CocoBase API.

**Applies to:** Collections API, Auth Collections API, Realtime API

---

## Table of Contents

1. [Basic Filtering](#basic-filtering)
2. [Filter Operators](#filter-operators)
3. [AND Conditions](#and-conditions)
4. [OR Conditions](#or-conditions)
5. [Complex Queries](#complex-queries)
6. [JSONB Field Filtering](#jsonb-field-filtering)
7. [Array Operations](#array-operations)
8. [Null Checks](#null-checks)
9. [Best Practices](#best-practices)

---

## Basic Filtering

### Exact Match

Filter by exact field value:

```bash
# Find users with status "active"
curl "https://api.cocobase.buzz/collections/users/documents?status=active" \
  -H "X-API-Key: your-api-key"

# Explicit equality operator
curl "https://api.cocobase.buzz/collections/users/documents?status_eq=active" \
  -H "X-API-Key: your-api-key"
```

**JavaScript:**
```javascript
const response = await fetch(
  'https://api.cocobase.buzz/collections/users/documents?status=active',
  {
    headers: { 'X-API-Key': 'your-api-key' }
  }
);
```

---

## Filter Operators

### Comparison Operators

| Operator | Description | Example | Matches |
|----------|-------------|---------|---------|
| `eq` | Equal to | `age_eq=25` | `{"age": 25}` |
| `ne` | Not equal to | `status_ne=inactive` | `{"status": "active"}` |
| `gt` | Greater than | `age_gt=18` | `{"age": 19}` |
| `gte` | Greater than or equal | `age_gte=18` | `{"age": 18}` or `{"age": 25}` |
| `lt` | Less than | `age_lt=65` | `{"age": 64}` |
| `lte` | Less than or equal | `age_lte=65` | `{"age": 65}` or `{"age": 50}` |

**Examples:**

```bash
# Users over 18
curl "https://api.cocobase.buzz/collections/users/documents?age_gte=18" \
  -H "X-API-Key: your-api-key"

# Users under 65
curl "https://api.cocobase.buzz/collections/users/documents?age_lt=65" \
  -H "X-API-Key: your-api-key"

# Users NOT inactive
curl "https://api.cocobase.buzz/collections/users/documents?status_ne=inactive" \
  -H "X-API-Key: your-api-key"
```

### String Operators

| Operator | Description | Example | Matches |
|----------|-------------|---------|---------|
| `contains` | Contains substring | `name_contains=john` | `{"name": "John Doe"}` |
| `startswith` | Starts with | `email_startswith=admin` | `{"email": "admin@example.com"}` |
| `endswith` | Ends with | `email_endswith=@gmail.com` | `{"email": "user@gmail.com"}` |

**Note:** All string comparisons are **case-insensitive**.

**Examples:**

```bash
# Search by name
curl "https://api.cocobase.buzz/collections/users/documents?name_contains=john" \
  -H "X-API-Key: your-api-key"

# Gmail users only
curl "https://api.cocobase.buzz/collections/users/documents?email_endswith=@gmail.com" \
  -H "X-API-Key: your-api-key"

# Admin emails
curl "https://api.cocobase.buzz/collections/users/documents?email_startswith=admin" \
  -H "X-API-Key: your-api-key"
```

**JavaScript:**
```javascript
// Search for users with "john" in name
const params = new URLSearchParams({
  name_contains: 'john'
});

const response = await fetch(
  `https://api.cocobase.buzz/collections/users/documents?${params}`,
  {
    headers: { 'X-API-Key': 'your-api-key' }
  }
);
```

### List Operators

| Operator | Description | Example | Matches |
|----------|-------------|---------|---------|
| `in` | In list | `role_in=admin,moderator` | `{"role": "admin"}` |
| `notin` | Not in list | `status_notin=deleted,archived` | `{"status": "active"}` |

**Examples:**

```bash
# Admins or moderators
curl "https://api.cocobase.buzz/collections/users/documents?role_in=admin,moderator" \
  -H "X-API-Key: your-api-key"

# Exclude deleted and archived
curl "https://api.cocobase.buzz/collections/users/documents?status_notin=deleted,archived" \
  -H "X-API-Key: your-api-key"
```

**JavaScript:**
```javascript
// Find admins, moderators, or editors
const params = new URLSearchParams({
  role_in: 'admin,moderator,editor'
});

const response = await fetch(
  `https://api.cocobase.buzz/collections/users/documents?${params}`,
  {
    headers: { 'X-API-Key': 'your-api-key' }
  }
);
```

---

## AND Conditions

By default, multiple filters are combined with **AND** logic.

**Example:**

```bash
# Active users over 18
curl "https://api.cocobase.buzz/collections/users/documents?status=active&age_gte=18" \
  -H "X-API-Key: your-api-key"
```

This matches documents where:
- `status` equals "active" **AND**
- `age` is greater than or equal to 18

**More Examples:**

```bash
# Active premium users over 18
curl "https://api.cocobase.buzz/collections/users/documents?status=active&plan=premium&age_gte=18" \
  -H "X-API-Key: your-api-key"

# Gmail users created after Jan 1, 2024
curl "https://api.cocobase.buzz/collections/users/documents?email_endswith=@gmail.com&created_at_gte=2024-01-01" \
  -H "X-API-Key: your-api-key"
```

**JavaScript:**
```javascript
const params = new URLSearchParams({
  status: 'active',
  plan: 'premium',
  age_gte: '18'
});

const response = await fetch(
  `https://api.cocobase.buzz/collections/users/documents?${params}`,
  {
    headers: { 'X-API-Key': 'your-api-key' }
  }
);
```

---

## OR Conditions

Use OR conditions when you want documents matching **any** of the conditions.

### Basic OR

Prefix filter parameters with `[or]`:

```bash
# Users who are EITHER admins OR moderators
curl "https://api.cocobase.buzz/collections/users/documents?[or]role=admin&[or]role=moderator" \
  -H "X-API-Key: your-api-key"
```

This matches documents where:
- `role` equals "admin" **OR**
- `role` equals "moderator"

**More Examples:**

```bash
# Users over 65 OR VIP status
curl "https://api.cocobase.buzz/collections/users/documents?[or]age_gte=65&[or]status=vip" \
  -H "X-API-Key: your-api-key"

# Free users OR trial users
curl "https://api.cocobase.buzz/collections/users/documents?[or]plan=free&[or]plan=trial" \
  -H "X-API-Key: your-api-key"
```

### Named OR Groups

Create multiple independent OR groups using `[or:name]`:

```bash
# (Young adults: 18-25) OR (Seniors: 60-70)
curl "https://api.cocobase.buzz/collections/users/documents?[or:young]age_gte=18&[or:young]age_lte=25&[or:senior]age_gte=60&[or:senior]age_lte=70" \
  -H "X-API-Key: your-api-key"
```

This creates two OR groups:
- **Group "young":** age >= 18 AND age <= 25
- **Group "senior":** age >= 60 AND age <= 70

Then returns documents matching **either** group.

**More Examples:**

```bash
# (Premium in US) OR (Free in UK)
curl "https://api.cocobase.buzz/collections/users/documents?[or:premium_us]plan=premium&[or:premium_us]country=US&[or:free_uk]plan=free&[or:free_uk]country=UK" \
  -H "X-API-Key: your-api-key"
```

### Multi-Field OR Search

Search across multiple fields with `__or__`:

```bash
# Search "john" in name OR email
curl "https://api.cocobase.buzz/collections/users/documents?name__or__email_contains=john" \
  -H "X-API-Key: your-api-key"
```

This matches documents where:
- `name` contains "john" **OR**
- `email` contains "john"

**JavaScript:**
```javascript
// Search across multiple fields
const params = new URLSearchParams({
  'name__or__email_contains': 'john'
});

const response = await fetch(
  `https://api.cocobase.buzz/collections/users/documents?${params}`,
  {
    headers: { 'X-API-Key': 'your-api-key' }
  }
);
```

---

## Complex Queries

### Combining AND + OR

Combine AND and OR conditions for complex queries:

```bash
# Active users who are (admins OR moderators)
curl "https://api.cocobase.buzz/collections/users/documents?status=active&[or]role=admin&[or]role=moderator" \
  -H "X-API-Key": your-api-key"
```

Logic:
- `status` equals "active" **AND**
- (`role` equals "admin" **OR** `role` equals "moderator")

**More Examples:**

```bash
# Premium users in (US OR UK)
curl "https://api.cocobase.buzz/collections/users/documents?plan=premium&[or]country=US&[or]country=UK" \
  -H "X-API-Key: your-api-key"

# Active users who are (under 18 OR over 65)
curl "https://api.cocobase.buzz/collections/users/documents?status=active&[or]age_lt=18&[or]age_gte=65" \
  -H "X-API-Key: your-api-key"
```

### Range Queries

```bash
# Users between 18 and 65
curl "https://api.cocobase.buzz/collections/users/documents?age_gte=18&age_lte=65" \
  -H "X-API-Key: your-api-key"

# Documents created in January 2024
curl "https://api.cocobase.buzz/collections/posts/documents?created_at_gte=2024-01-01&created_at_lt=2024-02-01" \
  -H "X-API-Key: your-api-key"
```

### Exclusion Queries

```bash
# All users EXCEPT deleted and archived
curl "https://api.cocobase.buzz/collections/users/documents?status_notin=deleted,archived" \
  -H "X-API-Key: your-api-key"

# Non-admin users
curl "https://api.cocobase.buzz/collections/users/documents?role_ne=admin" \
  -H "X-API-Key: your-api-key"
```

---

## JSONB Field Filtering

For **Auth Collections**, user data is stored in a JSONB `data` field. Filter by JSONB fields using `data.field_name`:

```bash
# Find users by username
curl "https://api.cocobase.buzz/auth-collections/users?data.username=johndoe" \
  -H "X-API-Key: your-api-key"

# Find users over 18
curl "https://api.cocobase.buzz/auth-collections/users?data.age_gte=18" \
  -H "X-API-Key: your-api-key"

# Find admins
curl "https://api.cocobase.buzz/auth-collections/users?data.role=admin" \
  -H "X-API-Key: your-api-key"
```

**All operators work on JSONB fields:**

```bash
# Users with bio containing "developer"
curl "https://api.cocobase.buzz/auth-collections/users?data.bio_contains=developer" \
  -H "X-API-Key: your-api-key"

# Users with username starting with "admin"
curl "https://api.cocobase.buzz/auth-collections/users?data.username_startswith=admin" \
  -H "X-API-Key: your-api-key"

# Premium or VIP users
curl "https://api.cocobase.buzz/auth-collections/users?data.tier_in=premium,vip" \
  -H "X-API-Key: your-api-key"
```

**JavaScript:**
```javascript
// Filter by JSONB field
const params = new URLSearchParams({
  'data.role': 'admin',
  'data.age_gte': '18'
});

const response = await fetch(
  `https://api.cocobase.buzz/auth-collections/users?${params}`,
  {
    headers: { 'X-API-Key': 'your-api-key' }
  }
);
```

---

## Array Operations

### Array Contains (Auth Collections only)

Check if a JSONB array field contains a specific value:

```bash
# Find users who have "user_123" in their followers array
curl "https://api.cocobase.buzz/auth-collections/users?data.followers_ids_array_contains=user_123" \
  -H "X-API-Key: your-api-key"

# Find users who have "premium" in their badges array
curl "https://api.cocobase.buzz/auth-collections/users?data.badges_array_contains=premium" \
  -H "X-API-Key: your-api-key"
```

**Use Case - Social Features:**
```bash
# Find all users who follow "user_123"
curl "https://api.cocobase.buzz/auth-collections/users?data.following_ids_array_contains=user_123" \
  -H "X-API-Key: your-api-key"
```

---

## Null Checks

Check if a field is null or missing:

```bash
# Find users with no bio
curl "https://api.cocobase.buzz/auth-collections/users?data.bio_isnull=true" \
  -H "X-API-Key: your-api-key"

# Find users WITH a bio
curl "https://api.cocobase.buzz/auth-collections/users?data.bio_isnull=false" \
  -H "X-API-Key: your-api-key"

# Documents not yet deleted
curl "https://api.cocobase.buzz/collections/posts/documents?deleted_at_isnull=true" \
  -H "X-API-Key: your-api-key"
```

**JavaScript:**
```javascript
// Find documents with missing fields
const params = new URLSearchParams({
  'bio_isnull': 'true'
});

const response = await fetch(
  `https://api.cocobase.buzz/collections/users/documents?${params}`,
  {
    headers: { 'X-API-Key': 'your-api-key' }
  }
);
```

---

## Best Practices

### 1. Use Specific Filters

Filter on the server, not the client:

```bash
# ✅ Good: Filter on server
?status=active&age_gte=18&plan=premium

# ❌ Bad: Fetch everything, filter client-side
# This wastes bandwidth and is slower
```

### 2. Use Indexes for Common Queries

If you frequently filter by specific fields, contact support to add database indexes:

```bash
# Frequently queried fields should be indexed
?email=john@example.com
?status=active
?created_at_gte=2024-01-01
```

### 3. Limit Results with Pagination

Always use `limit` for large datasets:

```bash
# ✅ Good: Paginate results
?limit=50&offset=0

# ❌ Bad: Fetch all (may timeout or use too much memory)
```

### 4. Combine Filters Efficiently

Order filters from most to least selective:

```bash
# ✅ Good: Most selective first
?email=specific@example.com&status=active

# Still works, but less efficient:
?status=active&email=specific@example.com
```

### 5. Use IN operator for Multiple Values

Don't make multiple requests:

```bash
# ✅ Good: Single request with IN
?role_in=admin,moderator,editor

# ❌ Bad: Multiple requests
# Request 1: ?role=admin
# Request 2: ?role=moderator
# Request 3: ?role=editor
```

### 6. Cache Common Queries

Cache frequently requested data on the client:

```javascript
// Cache results for 5 minutes
const cache = new Map();
const CACHE_TTL = 5 * 60 * 1000;

async function fetchUsers(filters) {
  const cacheKey = JSON.stringify(filters);
  const cached = cache.get(cacheKey);

  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    return cached.data;
  }

  const params = new URLSearchParams(filters);
  const response = await fetch(
    `https://api.cocobase.buzz/collections/users/documents?${params}`,
    {
      headers: { 'X-API-Key': 'your-api-key' }
    }
  );

  const data = await response.json();
  cache.set(cacheKey, { data, timestamp: Date.now() });

  return data;
}
```

### 7. Use count=false for Faster Queries

Skip counting when you don't need it:

```bash
# ✅ Faster: Skip count on paginated pages
?limit=50&offset=50&count=false

# Only count on first page
?limit=50&offset=0&count=true
```

---

## Realtime Filtering

All these filter operators work with **Realtime Collection Watch** too:

```javascript
const ws = new WebSocket('wss://api.cocobase.buzz/realtime/collections/users');

ws.onopen = () => {
  ws.send(JSON.stringify({
    api_key: "your-api-key",
    filters: {
      "status": "active",
      "age_gte": "18",
      "role_in": "admin,moderator"
    }
  }));
};

// Only receive events for documents matching these filters
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Filtered event:', data);
};
```

---

## Query Examples by Use Case

### E-commerce

```bash
# Active orders over $100
?status=active&total_gte=100

# Orders from last 30 days
?created_at_gte=2024-01-15

# Orders with (pending OR processing) status
?[or]status=pending&[or]status=processing

# Premium customers in US or UK
?customer_tier=premium&[or]country=US&[or]country=UK
```

### Social Media

```bash
# Posts with over 100 likes
?likes_gte=100

# Posts from specific users
?author_id_in=user_123,user_456,user_789

# Popular posts from last week
?created_at_gte=2024-01-08&likes_gte=50

# Posts containing "tutorial" OR "guide"
?title__or__content_contains=tutorial
```

### User Management

```bash
# Active admins or moderators
?status=active&[or]role=admin&[or]role=moderator

# Users who haven't logged in recently
?last_login_lt=2024-01-01

# Gmail users who signed up in January
?email_endswith=@gmail.com&created_at_gte=2024-01-01&created_at_lt=2024-02-01

# Users with no profile picture
?data.profile_picture_isnull=true
```

---

## Next Steps

- **[Collections API](./collections.md)** - Full collections documentation
- **[Auth Collections](./auth-collections.md)** - User authentication
- **[Realtime](./realtime.md)** - Real-time filtering
- **[Relationships](./relationships.md)** - Document relationships

---

**Need Help?** Contact support@cocobase.com
