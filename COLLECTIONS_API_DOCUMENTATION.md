# CocoBase Collections API Documentation

## Table of Contents

1. [Introduction](#introduction)
2. [Authentication](#authentication)
3. [Collections Management](#collections-management)
4. [Documents Management](#documents-management)
5. [Querying & Filtering](#querying--filtering)
6. [Relationships & Population](#relationships--population)
7. [Advanced Features](#advanced-features)
8. [Batch Operations](#batch-operations)
9. [Limitations](#limitations)

---

## Introduction

The CocoBase Collections API provides a flexible, NoSQL-like database system for storing and querying JSON documents. Each collection is a container for documents with dynamic schemas, similar to MongoDB or Firebase.

### Key Concepts

- **Collection**: A container for related documents (like a table in SQL)
- **Document**: A JSON object with an auto-generated ID and custom data
- **Schema**: Optional structure definition for your documents
- **Relationships**: Link documents across collections using foreign keys

---

## Authentication

All API requests require authentication using an API key in the request header:

```
X-Api-Key: your_api_key_here
```

**Example:**

```bash
curl -H "X-Api-Key: abc123..." https://api.cocobase.com/collections
```

---

## Collections Management

### Create a Collection

**Endpoint:** `POST /collections/`

**Request Body:**

```json
{
  "name": "users"
}
```

**Response:**

```json
{
  "id": "uuid-here",
  "name": "users",
  "created_at": "2025-10-31T12:00:00"
}
```

### List All Collections

**Endpoint:** `GET /collections/`

**Response:**

```json
[
  {
    "id": "uuid-1",
    "name": "users",
    "created_at": "2025-10-31T12:00:00"
  },
  {
    "id": "uuid-2",
    "name": "posts",
    "created_at": "2025-10-31T12:00:00"
  }
]
```

### Get a Collection

**Endpoint:** `GET /collections/{collection_name_or_id}`

### Update a Collection

**Endpoint:** `PATCH /collections/{collection_name_or_id}`

**Request Body:**

```json
{
  "name": "new_name"
}
```

### Delete a Collection

**Endpoint:** `DELETE /collections/{collection_name_or_id}`

⚠️ **Warning:** This deletes all documents in the collection!

---

## Documents Management

### Create a Document

**Endpoint:** `POST /collections/{collection_name}/documents`

**Request Body:**

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "age": 30,
  "role": "admin"
}
```

**Response:**

```json
{
  "id": "doc-uuid",
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "age": 30,
    "role": "admin"
  },
  "created_at": "2025-10-31T12:00:00"
}
```

### Get a Document

**Endpoint:** `GET /collections/{collection_name}/documents/{document_id}`

**With Relationships:**

```
GET /collections/posts/documents/doc-123?populate=author&populate=category
```

### Update a Document

**Endpoint:** `PATCH /collections/{collection_name}/documents/{document_id}`

**Request Body:**

```json
{
  "age": 31,
  "status": "active"
}
```

### Delete a Document

**Endpoint:** `DELETE /collections/{collection_name}/documents/{document_id}`

---

## Querying & Filtering

### List Documents with Filters

**Endpoint:** `GET /collections/{collection_name}/documents`

### Query Parameters

#### Basic Filters

Query documents using field equality:

```
GET /collections/users/documents?role=admin&status=active
```

#### Operators

Use operators to create complex filters:

| Operator       | Description           | Example                        |
| -------------- | --------------------- | ------------------------------ |
| `__gt`         | Greater than          | `age__gt=18`                   |
| `__gte`        | Greater than or equal | `age__gte=21`                  |
| `__lt`         | Less than             | `price__lt=100`                |
| `__lte`        | Less than or equal    | `stock__lte=10`                |
| `__ne`         | Not equal             | `status__ne=deleted`           |
| `__in`         | In array              | `role__in=admin,editor`        |
| `__contains`   | Contains text         | `name__contains=John`          |
| `__startswith` | Starts with           | `email__startswith=admin`      |
| `__endswith`   | Ends with             | `email__endswith=@company.com` |

**Examples:**

Find users over 18:

```
GET /collections/users/documents?age__gte=18
```

Find products under $50:

```
GET /collections/products/documents?price__lt=50
```

Find users with specific roles:

```
GET /collections/users/documents?role__in=admin,moderator
```

Find users whose email contains "gmail":

```
GET /collections/users/documents?email__contains=gmail
```

#### Pagination

```
GET /collections/users/documents?limit=50&offset=100
```

- `limit`: Number of documents to return (default: 100, max: 1000)
- `offset`: Number of documents to skip

#### Sorting

```
GET /collections/users/documents?sort_by=created_at&order=desc
```

- `sort_by`: Field to sort by
- `order`: `asc` (ascending) or `desc` (descending)

#### Field Selection

Return only specific fields:

```
GET /collections/users/documents?select=name&select=email&select=age
```

Returns:

```json
[
  {
    "id": "doc-1",
    "name": "John Doe",
    "email": "john@example.com",
    "age": 30
  }
]
```

---

## Relationships & Population

### Setting Up Relationships

Documents can reference other documents using foreign keys. By convention, use `{collection_name}_id` format:

**Example - Posts referencing Authors:**

```json
{
  "title": "My First Post",
  "content": "Hello World",
  "author_id": "user-123",
  "category_id": "cat-456"
}
```

### Populating Relationships

Use the `populate` parameter to automatically fetch related documents:

**Basic Population:**

```
GET /collections/posts/documents?populate=author
```

**Response:**

```json
[
  {
    "id": "post-1",
    "title": "My First Post",
    "content": "Hello World",
    "author_id": "user-123",
    "author": {
      "id": "user-123",
      "name": "John Doe",
      "email": "john@example.com"
    }
  }
]
```

### Multiple Populations

Populate multiple relationships at once:

```
GET /collections/posts/documents?populate=author&populate=category
```

### Nested Populations

Populate relationships within relationships:

```
GET /collections/comments/documents?populate=post.author
```

This populates the comment's post, and then the post's author.

**Response:**

```json
[
  {
    "id": "comment-1",
    "text": "Great post!",
    "post_id": "post-1",
    "post": {
      "id": "post-1",
      "title": "My First Post",
      "author_id": "user-123",
      "author": {
        "id": "user-123",
        "name": "John Doe"
      }
    }
  }
]
```

### Filtering by Relationship Fields

Query documents based on related document data:

**Find posts by admin authors:**

```
GET /collections/posts/documents?author.role=admin&populate=author
```

**Find posts with specific author email:**

```
GET /collections/posts/documents?author.email__contains=john&populate=author
```

**Operators work on relationships too:**

```
GET /collections/posts/documents?author.age__gte=18&category.name__ne=archived
```

### Selecting Fields with Relationships

Combine field selection with population:

```
GET /collections/posts/documents?select=title&select=author.name&select=author.email&populate=author
```

---

## Advanced Features

### Count Documents

**Endpoint:** `GET /collections/{collection_name}/query/documents/count`

**With Filters:**

```
GET /collections/users/query/documents/count?role=admin&status=active
```

**Response:**

```json
{
  "count": 42
}
```

### Aggregate Documents

**Endpoint:** `GET /collections/{collection_name}/query/documents/aggregate`

**Parameters:**

- `field`: Field to aggregate
- `operation`: `sum`, `avg`, `min`, `max`

**Examples:**

Average age:

```
GET /collections/users/query/documents/aggregate?field=age&operation=avg
```

Total sales:

```
GET /collections/orders/query/documents/aggregate?field=total&operation=sum
```

**With Filters:**

```
GET /collections/orders/query/documents/aggregate?field=total&operation=sum&status=completed
```

**Response:**

```json
{
  "result": 15420.5
}
```

### Group By

**Endpoint:** `GET /collections/{collection_name}/query/documents/group-by`

Group documents by a field value:

```
GET /collections/users/query/documents/group-by?field=role
```

**Response:**

```json
[
  {
    "value": "admin",
    "count": 5
  },
  {
    "value": "user",
    "count": 150
  }
]
```

**With Filters:**

```
GET /collections/orders/query/documents/group-by?field=status&created_at__gte=2025-01-01
```

### Get Collection Schema

**Endpoint:** `GET /collections/{collection_name}/query/schema`

Returns the inferred schema from your documents:

**Response:**

```json
{
  "fields": [
    {
      "name": "name",
      "type": "string",
      "nullable": false
    },
    {
      "name": "age",
      "type": "integer",
      "nullable": true
    },
    {
      "name": "email",
      "type": "string",
      "nullable": false
    }
  ]
}
```

### Export Collection

**Endpoint:** `GET /collections/{collection_name}/export`

**Parameters:**

- `format`: `json` or `csv`
- `populate`: (optional) Populate relationships in export

**JSON Export:**

```
GET /collections/users/export?format=json
```

**CSV Export with Relationships:**

```
GET /collections/posts/export?format=csv&populate=author
```

---

## Batch Operations

### Batch Create Documents

**Endpoint:** `POST /collections/{collection_name}/batch/documents/create`

Create multiple documents in a single request:

**Request Body:**

```json
{
  "documents": [
    {
      "name": "John Doe",
      "email": "john@example.com"
    },
    {
      "name": "Jane Smith",
      "email": "jane@example.com"
    },
    {
      "name": "Bob Johnson",
      "email": "bob@example.com"
    }
  ]
}
```

**Response:**

```json
{
  "created": 3,
  "documents": [
    {
      "id": "doc-1",
      "data": { "name": "John Doe", "email": "john@example.com" }
    },
    {
      "id": "doc-2",
      "data": { "name": "Jane Smith", "email": "jane@example.com" }
    },
    {
      "id": "doc-3",
      "data": { "name": "Bob Johnson", "email": "bob@example.com" }
    }
  ]
}
```

### Batch Update Documents

**Endpoint:** `PATCH /collections/{collection_name}/batch/documents/update`

Update multiple documents by ID:

**Request Body:**

```json
{
  "updates": [
    {
      "id": "doc-1",
      "data": { "status": "active" }
    },
    {
      "id": "doc-2",
      "data": { "status": "inactive" }
    }
  ]
}
```

**Response:**

```json
{
  "updated": 2
}
```

### Batch Delete Documents

**Endpoint:** `DELETE /collections/{collection_name}/batch/documents/delete`

Delete multiple documents by ID:

**Request Body:**

```json
{
  "ids": ["doc-1", "doc-2", "doc-3"]
}
```

**Response:**

```json
{
  "deleted": 3
}
```

---

## Limitations

### 1. Document Size

- **Maximum document size:** 1 MB per document
- **Recommendation:** Store large files (images, videos) in separate storage and reference them by URL

### 2. Query Performance

#### Pagination Limits

- **Maximum limit per request:** 1,000 documents
- **Default limit:** 100 documents
- Use pagination for larger datasets

#### Deep Nesting

- **Maximum relationship nesting depth:** 3 levels
- Example: `comment.post.author.company` (4 levels) is NOT supported
- Example: `comment.post.author` (3 levels) is supported

#### Complex Queries

- Queries with multiple relationship filters may be slower on large datasets
- **Recommendation:** Index frequently queried fields (coming soon)

### 3. Relationship Constraints

#### Foreign Key Validation

- Foreign keys are **not automatically validated**
- You can reference non-existent documents (they'll just be null when populated)
- **Recommendation:** Validate foreign keys in your application logic

#### Circular References

- Circular relationships can cause infinite loops if not careful
- Example: `user.posts[].author` where author references the same user
- **Recommendation:** Limit nesting depth when dealing with circular references

#### Collection Name Resolution

- Collections must follow naming: `{singular}_id` → `{plural}` collection
- Example: `author_id` looks for collection named `authors`
- Example: `category_id` looks for collection named `categories`
- **Limitation:** Custom pluralization not supported (e.g., `person_id` → `persons`, not `people`)

### 4. Data Types

#### JSON Only

- All data is stored as JSON
- No native support for binary data
- Dates are stored as ISO 8601 strings
- **Recommendation:** Store dates as `"2025-10-31T12:00:00Z"` for proper sorting

#### No Transaction Support

- Batch operations are not atomic
- If a batch operation fails partway through, some documents may be created/updated while others fail
- **Recommendation:** Implement retry logic in your application

### 5. Schema Flexibility

#### Dynamic Schema

- No schema enforcement (advantage and limitation)
- Documents in the same collection can have different fields
- **Recommendation:** Use consistent field names and types in your application

#### Type Coercion

- String fields containing numbers: `"123"` vs `123` are different
- Affects filtering: `age=123` won't match `age="123"`
- **Recommendation:** Be consistent with data types

### 6. Aggregations

#### Limited Operations

- Only supports: `sum`, `avg`, `min`, `max`
- No support for complex aggregations like `median`, `percentile`, etc.
- **Workaround:** Fetch data and calculate in your application

#### Numeric Fields Only

- Aggregations only work on numeric fields
- Text fields will be ignored

### 7. Search Capabilities

#### Text Search

- `__contains` performs case-insensitive substring match
- No full-text search or fuzzy matching
- No relevance scoring
- **Limitation:** Not suitable for advanced search features

#### Regular Expressions

- Not currently supported
- **Workaround:** Use `__contains`, `__startswith`, `__endswith` operators

### 8. Rate Limits

#### API Requests

- Rate limits depend on your plan
- Typically: 1,000 requests/minute for free tier
- Check your plan details for specific limits

#### Bulk Operations

- Batch create: Max 1,000 documents per request
- Batch update: Max 1,000 documents per request
- Batch delete: Max 1,000 IDs per request

### 9. Storage Limits

#### Collection Count

- Depends on your plan
- Free tier: Up to 10 collections

#### Document Count

- No hard limit per collection
- Performance may degrade with millions of documents
- **Recommendation:** Consider archiving old data

### 10. Real-time Features

#### No Built-in Subscriptions

- No WebSocket or Server-Sent Events for real-time updates
- **Workaround:** Implement polling in your application
- **Coming Soon:** WebSocket support for real-time updates

---

## Best Practices

### 1. Naming Conventions

- Use lowercase for collection names: `users`, not `Users`
- Use snake_case for field names: `first_name`, not `firstName`
- Follow foreign key convention: `author_id`, `category_id`

### 2. Query Optimization

- Use field selection to fetch only needed data
- Limit population depth to 2-3 levels maximum
- Use pagination for large result sets
- Add filters to narrow down results

### 3. Data Modeling

- Normalize data when relationships are complex
- Denormalize data for frequently accessed relationships
- Store commonly filtered fields at document root level
- Use consistent data types across documents

### 4. Error Handling

- Always check response status codes
- Implement retry logic for failed batch operations
- Validate foreign keys before creating relationships
- Handle null values when populating optional relationships

### 5. Security

- Never expose your API key in client-side code
- Use environment variables for API keys
- Implement proper authentication in your application
- Validate user input before sending to API

---

## Example Use Cases

### Blog Platform

**Collections:**

- `users`: Author information
- `posts`: Blog posts with `author_id`
- `comments`: Comments with `post_id` and `author_id`
- `categories`: Post categories

**Query Examples:**

List recent posts with author info:

```
GET /collections/posts/documents?sort_by=created_at&order=desc&limit=10&populate=author
```

Find all posts in a category:

```
GET /collections/posts/documents?category_id=cat-123&populate=category
```

Get comments for a post with author details:

```
GET /collections/comments/documents?post_id=post-123&populate=author&populate=post
```

### E-commerce Platform

**Collections:**

- `products`: Product catalog
- `orders`: Customer orders
- `order_items`: Line items with `product_id` and `order_id`
- `customers`: Customer information

**Query Examples:**

Find products under $50:

```
GET /collections/products/documents?price__lt=50&stock__gt=0
```

Get order details with items and products:

```
GET /collections/orders/documents/order-123?populate=order_items.product
```

Calculate total sales:

```
GET /collections/orders/query/documents/aggregate?field=total&operation=sum&status=completed
```

---

## Support

For additional help or feature requests, contact support or visit our documentation at [https://docs.cocobase.com](https://docs.cocobase.com).
