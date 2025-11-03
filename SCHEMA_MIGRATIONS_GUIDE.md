# Schema Migrations API - Complete Guide

## 🎯 Overview

The Schema Migrations API allows you to make **structural changes** to your collections and fields without manually updating every document.

**What You Can Do:**

- ✅ Rename collections
- ✅ Rename fields across all documents
- ✅ Add new fields with default values
- ✅ Delete fields from all documents
- ✅ Change field types (with conversions)
- ✅ Merge multiple fields into one
- ✅ Split one field into multiple fields
- ✅ Analyze field usage before migrating

**Base URL:** `/migrations`

---

## 📋 Table of Contents

1. [Collection Migrations](#collection-migrations)
2. [Field Migrations](#field-migrations)
3. [Advanced Operations](#advanced-operations)
4. [Utility Endpoints](#utility-endpoints)
5. [Best Practices](#best-practices)
6. [Examples](#examples)

---

## 🗂️ Collection Migrations

### 1. Rename Collection

**Endpoint:** `POST /migrations/rename-collection`

Rename a collection while preserving all documents and IDs.

**Request:**

```json
{
  "old_name": "users",
  "new_name": "customers"
}
```

**Response:**

```json
{
  "success": true,
  "message": "Collection renamed from 'users' to 'customers'",
  "documents_affected": 0,
  "execution_time_ms": 45,
  "details": {
    "collection_id": "col-abc123",
    "old_name": "users",
    "new_name": "customers"
  }
}
```

**cURL Example:**

```bash
curl -X POST "https://api.cocobase.com/migrations/rename-collection" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "old_name": "users",
    "new_name": "customers"
  }'
```

---

## 🔧 Field Migrations

### 2. Rename Field

**Endpoint:** `POST /migrations/rename-field`

Rename a field in **all documents** of a collection.

**Request:**

```json
{
  "collection": "users",
  "old_field_name": "fullName",
  "new_field_name": "full_name"
}
```

**What Happens:**

**Before:**

```json
[
  { "id": "1", "fullName": "John Doe", "age": 30 },
  { "id": "2", "fullName": "Jane Smith", "age": 25 }
]
```

**After:**

```json
[
  { "id": "1", "full_name": "John Doe", "age": 30 },
  { "id": "2", "full_name": "Jane Smith", "age": 25 }
]
```

**Response:**

```json
{
  "success": true,
  "message": "Field 'fullName' renamed to 'full_name' in 2 documents",
  "documents_affected": 2,
  "execution_time_ms": 120,
  "details": {
    "collection": "users",
    "old_field": "fullName",
    "new_field": "full_name"
  }
}
```

---

### 3. Add Field

**Endpoint:** `POST /migrations/add-field`

Add a new field with a default value to **all documents**.

**Request:**

```json
{
  "collection": "users",
  "field_name": "status",
  "default_value": "active"
}
```

**What Happens:**

**Before:**

```json
[
  { "id": "1", "name": "John" },
  { "id": "2", "name": "Jane" }
]
```

**After:**

```json
[
  { "id": "1", "name": "John", "status": "active" },
  { "id": "2", "name": "Jane", "status": "active" }
]
```

**Different Default Values:**

```json
// String
{"field_name": "role", "default_value": "user"}

// Number
{"field_name": "credits", "default_value": 100}

// Boolean
{"field_name": "is_verified", "default_value": false}

// Array
{"field_name": "tags", "default_value": []}

// Object
{"field_name": "settings", "default_value": {"theme": "light"}}

// Null
{"field_name": "deleted_at", "default_value": null}
```

---

### 4. Delete Field

**Endpoint:** `POST /migrations/delete-field`

⚠️ **Warning:** This permanently deletes the field from all documents!

**Request:**

```json
{
  "collection": "users",
  "field_name": "legacy_id"
}
```

**What Happens:**

**Before:**

```json
[
  { "id": "1", "name": "John", "legacy_id": "old123" },
  { "id": "2", "name": "Jane", "legacy_id": "old456" }
]
```

**After:**

```json
[
  { "id": "1", "name": "John" },
  { "id": "2", "name": "Jane" }
]
```

**Response:**

```json
{
  "success": true,
  "message": "Field 'legacy_id' deleted from 2 documents",
  "documents_affected": 2,
  "execution_time_ms": 95
}
```

---

### 5. Change Field Type

**Endpoint:** `POST /migrations/change-field-type`

Convert field types across all documents.

**Supported Types:**

- `string` - Convert to string
- `number` - Convert to number (int or float)
- `boolean` - Convert to boolean
- `array` - Wrap in array
- `object` - Wrap in object

**Example 1: String to Number**

**Request:**

```json
{
  "collection": "products",
  "field_name": "price",
  "target_type": "number"
}
```

**Before:**

```json
{ "id": "1", "price": "99.99" }
```

**After:**

```json
{ "id": "1", "price": 99.99 }
```

---

**Example 2: String to Boolean (with conversion map)**

**Request:**

```json
{
  "collection": "users",
  "field_name": "is_active",
  "target_type": "boolean",
  "conversion_map": {
    "yes": true,
    "no": false,
    "active": true,
    "inactive": false,
    "1": true,
    "0": false
  }
}
```

**Before:**

```json
[
  { "id": "1", "is_active": "yes" },
  { "id": "2", "is_active": "no" },
  { "id": "3", "is_active": "active" }
]
```

**After:**

```json
[
  { "id": "1", "is_active": true },
  { "id": "2", "is_active": false },
  { "id": "3", "is_active": true }
]
```

---

**Example 3: Any to Array**

**Request:**

```json
{
  "collection": "products",
  "field_name": "category",
  "target_type": "array"
}
```

**Before:**

```json
{ "id": "1", "category": "electronics" }
```

**After:**

```json
{ "id": "1", "category": ["electronics"] }
```

---

## 🔀 Advanced Operations

### 6. Merge Fields

**Endpoint:** `POST /migrations/merge-fields`

Combine multiple fields into one.

**Strategies:**

- `concat` - Concatenate strings with separator
- `sum` - Sum numbers
- `array` - Create array from values
- `first` - Use first non-null value

**Example 1: Merge Names (concat)**

**Request:**

```json
{
  "collection": "users",
  "source_fields": ["first_name", "last_name"],
  "target_field": "full_name",
  "strategy": "concat",
  "separator": " "
}
```

**Before:**

```json
{ "id": "1", "first_name": "John", "last_name": "Doe" }
```

**After:**

```json
{
  "id": "1",
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe"
}
```

---

**Example 2: Calculate Total (sum)**

**Request:**

```json
{
  "collection": "orders",
  "source_fields": ["subtotal", "tax", "shipping"],
  "target_field": "total",
  "strategy": "sum"
}
```

**Before:**

```json
{
  "id": "1",
  "subtotal": 100,
  "tax": 8.5,
  "shipping": 12
}
```

**After:**

```json
{
  "id": "1",
  "subtotal": 100,
  "tax": 8.5,
  "shipping": 12,
  "total": 120.5
}
```

---

**Example 3: Create Tags Array (array)**

**Request:**

```json
{
  "collection": "products",
  "source_fields": ["category", "brand", "color"],
  "target_field": "tags",
  "strategy": "array"
}
```

**Before:**

```json
{
  "id": "1",
  "category": "electronics",
  "brand": "Apple",
  "color": "black"
}
```

**After:**

```json
{
  "id": "1",
  "category": "electronics",
  "brand": "Apple",
  "color": "black",
  "tags": ["electronics", "Apple", "black"]
}
```

---

### 7. Split Field

**Endpoint:** `POST /migrations/split-field`

Split one field into multiple fields.

**Request:**

```json
{
  "collection": "users",
  "source_field": "full_name",
  "target_fields": ["first_name", "last_name"],
  "separator": " "
}
```

**Before:**

```json
{ "id": "1", "full_name": "John Doe" }
```

**After:**

```json
{
  "id": "1",
  "full_name": "John Doe",
  "first_name": "John",
  "last_name": "Doe"
}
```

**More Parts Than Fields:**

```json
// Input: "John Michael Doe"
// Fields: ["first_name", "last_name"]
// Result: first_name="John", last_name="Michael" (rest ignored)
```

**Fewer Parts Than Fields:**

```json
// Input: "John"
// Fields: ["first_name", "last_name"]
// Result: first_name="John", last_name=null
```

---

## 🔍 Utility Endpoints

### 8. Analyze Collection Fields

**Endpoint:** `GET /migrations/{collection}/analyze-fields`

Analyze your collection's field structure before migrating.

**Request:**

```bash
GET /migrations/users/analyze-fields
```

**Response:**

```json
{
  "collection": "users",
  "collection_id": "col-abc123",
  "total_documents": 1000,
  "unique_fields": 8,
  "fields": {
    "name": {
      "types": ["str"],
      "present_in": 980,
      "missing_in": 20,
      "null_count": 15,
      "coverage_percentage": 98.0,
      "sample_values": ["John", "Jane", "Bob", "Alice", "Charlie"]
    },
    "age": {
      "types": ["int", "float"],
      "present_in": 950,
      "missing_in": 50,
      "null_count": 30,
      "coverage_percentage": 95.0,
      "sample_values": [25, 30, 35, 40, 28]
    },
    "email": {
      "types": ["str"],
      "present_in": 1000,
      "missing_in": 0,
      "null_count": 0,
      "coverage_percentage": 100.0,
      "sample_values": ["john@example.com", "jane@example.com"]
    }
  }
}
```

**Use Cases:**

- ✅ Find fields that need type conversion
- ✅ Identify inconsistent field names
- ✅ Check field coverage before adding/deleting
- ✅ Plan merge/split operations

---

### 9. Dry Run Migration

**Endpoint:** `POST /migrations/{collection}/dry-run`

Test a migration without making changes.

**Request:**

```bash
POST /migrations/users/dry-run?operation=rename-field
Content-Type: application/json

{
  "old_field_name": "fullName",
  "new_field_name": "full_name"
}
```

**Response:**

```json
{
  "collection": "users",
  "operation": "rename-field",
  "total_documents": 1000,
  "estimated_affected": 980,
  "sample_changes": [
    {
      "document_id": "doc-1",
      "before": { "fullName": "John Doe" },
      "after": { "full_name": "John Doe" }
    },
    {
      "document_id": "doc-2",
      "before": { "fullName": "Jane Smith" },
      "after": { "full_name": "Jane Smith" }
    }
  ],
  "warning": "This is a dry run. No changes were made."
}
```

---

## 💡 Best Practices

### 1. Always Analyze First

```bash
# Step 1: Analyze collection
GET /migrations/users/analyze-fields

# Step 2: Plan migration based on results

# Step 3: Dry run to test
POST /migrations/users/dry-run?operation=rename-field

# Step 4: Execute migration
POST /migrations/rename-field
```

---

### 2. Backup Before Major Changes

```bash
# Export collection before migration
GET /collections/users/export?format=json

# Save the response

# Then perform migration
POST /migrations/delete-field
```

---

### 3. Use Conversion Maps for Type Changes

**Bad (auto-conversion may fail):**

```json
{
  "field_name": "status",
  "target_type": "boolean"
}
// "active" → true (maybe)
// "inactive" → true (incorrect!)
```

**Good (explicit mapping):**

```json
{
  "field_name": "status",
  "target_type": "boolean",
  "conversion_map": {
    "active": true,
    "inactive": false,
    "pending": false,
    "deleted": false
  }
}
```

---

### 4. Incremental Migrations

Instead of one big migration:

```json
// ❌ Bad: Complex multi-step migration
{
  "operations": [
    "rename collection",
    "add 5 fields",
    "merge 3 fields",
    "change 2 types"
  ]
}
```

Do it step by step:

```bash
# ✅ Good: One operation at a time

# Step 1: Rename collection
POST /migrations/rename-collection

# Step 2: Add fields
POST /migrations/add-field

# Step 3: Merge fields
POST /migrations/merge-fields

# Step 4: Change types
POST /migrations/change-field-type
```

---

### 5. Monitor Execution Time

For large collections (>10k documents), migrations may take time:

```json
{
  "execution_time_ms": 5420, // 5.4 seconds
  "documents_affected": 50000
}
```

**Tips:**

- Run migrations during low-traffic periods
- Consider batching for very large collections
- Monitor database performance

---

## 📊 Real-World Examples

### Example 1: Normalize User Data

**Scenario:** Your user collection has inconsistent name fields.

**Step 1: Analyze**

```bash
GET /migrations/users/analyze-fields
```

**Result:**

```json
{
  "fields": {
    "fullName": { "present_in": 500 },
    "full_name": { "present_in": 300 },
    "name": { "present_in": 200 }
  }
}
```

**Step 2: Standardize to `full_name`**

```bash
# Rename fullName → full_name
POST /migrations/rename-field
{
  "collection": "users",
  "old_field_name": "fullName",
  "new_field_name": "full_name"
}

# Rename name → full_name (for the 200 docs)
POST /migrations/rename-field
{
  "collection": "users",
  "old_field_name": "name",
  "new_field_name": "full_name"
}
```

---

### Example 2: Add User Status System

**Scenario:** Add status tracking to existing users.

```bash
# Add status field with default
POST /migrations/add-field
{
  "collection": "users",
  "field_name": "status",
  "default_value": "active"
}

# Add created_at for audit
POST /migrations/add-field
{
  "collection": "users",
  "field_name": "created_at",
  "default_value": "2024-01-01T00:00:00Z"
}

# Add is_premium flag
POST /migrations/add-field
{
  "collection": "users",
  "field_name": "is_premium",
  "default_value": false
}
```

---

### Example 3: Migrate Legacy Data

**Scenario:** Legacy system had separate address fields.

**Before:**

```json
{
  "street": "123 Main St",
  "city": "New York",
  "state": "NY",
  "zip": "10001"
}
```

**Goal:**

```json
{
  "address": {
    "street": "123 Main St",
    "city": "New York",
    "state": "NY",
    "zip": "10001"
  }
}
```

**Solution:**

```bash
# Step 1: Create address object field
POST /migrations/add-field
{
  "collection": "users",
  "field_name": "address",
  "default_value": {}
}

# Step 2: Manual migration (custom script needed)
# This is complex - may need custom endpoint

# Step 3: Delete old fields
POST /migrations/delete-field
{"collection": "users", "field_name": "street"}

POST /migrations/delete-field
{"collection": "users", "field_name": "city"}

POST /migrations/delete-field
{"collection": "users", "field_name": "state"}

POST /migrations/delete-field
{"collection": "users", "field_name": "zip"}
```

---

### Example 4: Calculate Derived Fields

**Scenario:** Add full_name from first_name + last_name.

```bash
POST /migrations/merge-fields
{
  "collection": "users",
  "source_fields": ["first_name", "last_name"],
  "target_field": "full_name",
  "strategy": "concat",
  "separator": " "
}
```

**Result:**

```json
{
  "first_name": "John",
  "last_name": "Doe",
  "full_name": "John Doe" // ← Added
}
```

---

## ⚠️ Important Notes

### 1. Migrations Are Permanent

- ⚠️ Deleted fields cannot be recovered
- ⚠️ Type conversions may lose data precision
- ⚠️ Always test with dry-run first
- ⚠️ Export data before major migrations

---

### 2. Performance Considerations

**Small Collections (<1000 docs):**

- ✅ Instant migrations
- ✅ No performance impact

**Medium Collections (1k-10k docs):**

- ⚠️ 1-5 seconds execution time
- ⚠️ Minor performance impact

**Large Collections (>10k docs):**

- ⚠️ 5+ seconds execution time
- ⚠️ May impact database performance
- 💡 Run during low-traffic periods

---

### 3. Validation

**Field names:**

- Use lowercase with underscores (snake_case)
- Avoid special characters
- Keep names descriptive

**Type conversions:**

- Test with sample data first
- Use conversion maps for complex mappings
- Check for data loss

---

### 4. Rollback Strategy

Migrations don't have built-in rollback. To rollback:

```bash
# Option 1: Reverse migration
POST /migrations/rename-field
{
  "old_field_name": "full_name",  # Reverse the names
  "new_field_name": "fullName"
}

# Option 2: Restore from backup
POST /collections/users/import
{
  "data": [...backup data...]
}
```

---

## 🚀 Quick Reference

| Operation         | Endpoint                                      | Destructive? |
| ----------------- | --------------------------------------------- | ------------ |
| Rename Collection | `POST /migrations/rename-collection`          | ❌ No        |
| Rename Field      | `POST /migrations/rename-field`               | ❌ No        |
| Add Field         | `POST /migrations/add-field`                  | ❌ No        |
| Delete Field      | `POST /migrations/delete-field`               | ⚠️ Yes       |
| Change Type       | `POST /migrations/change-field-type`          | ⚠️ Maybe     |
| Merge Fields      | `POST /migrations/merge-fields`               | ❌ No        |
| Split Field       | `POST /migrations/split-field`                | ❌ No        |
| Analyze           | `GET /migrations/{collection}/analyze-fields` | ❌ No        |
| Dry Run           | `POST /migrations/{collection}/dry-run`       | ❌ No        |

---

## 🎯 Summary

**The Schema Migrations API lets you:**

- ✅ Rename collections and fields
- ✅ Add/delete fields across all documents
- ✅ Convert field types safely
- ✅ Merge and split fields
- ✅ Analyze before migrating
- ✅ Test with dry runs

**Always remember:**

1. Analyze first
2. Dry run to test
3. Backup critical data
4. Run during low traffic
5. Monitor execution time

Happy migrating! 🚀
