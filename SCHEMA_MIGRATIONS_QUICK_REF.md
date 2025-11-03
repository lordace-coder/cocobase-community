# Schema Migrations - Quick Reference

## 🚀 Quick Commands

### Rename Collection

```bash
curl -X POST "/migrations/rename-collection" \
  -d '{"old_name": "users", "new_name": "customers"}'
```

### Rename Field

```bash
curl -X POST "/migrations/rename-field" \
  -d '{
    "collection": "users",
    "old_field_name": "fullName",
    "new_field_name": "full_name"
  }'
```

### Add Field

```bash
curl -X POST "/migrations/add-field" \
  -d '{
    "collection": "users",
    "field_name": "status",
    "default_value": "active"
  }'
```

### Delete Field

```bash
curl -X POST "/migrations/delete-field" \
  -d '{
    "collection": "users",
    "field_name": "legacy_id"
  }'
```

### Change Field Type

```bash
curl -X POST "/migrations/change-field-type" \
  -d '{
    "collection": "products",
    "field_name": "price",
    "target_type": "number"
  }'
```

### Merge Fields

```bash
curl -X POST "/migrations/merge-fields" \
  -d '{
    "collection": "users",
    "source_fields": ["first_name", "last_name"],
    "target_field": "full_name",
    "strategy": "concat",
    "separator": " "
  }'
```

### Split Field

```bash
curl -X POST "/migrations/split-field" \
  -d '{
    "collection": "users",
    "source_field": "full_name",
    "target_fields": ["first_name", "last_name"],
    "separator": " "
  }'
```

### Analyze Collection

```bash
curl -X GET "/migrations/users/analyze-fields"
```

### Dry Run

```bash
curl -X POST "/migrations/users/dry-run?operation=rename-field" \
  -d '{
    "old_field_name": "fullName",
    "new_field_name": "full_name"
  }'
```

---

## 📊 Common Patterns

### Pattern 1: Standardize Field Names

```bash
# Analyze first
GET /migrations/users/analyze-fields

# Rename inconsistent fields
POST /migrations/rename-field
{"collection": "users", "old_field_name": "fullName", "new_field_name": "full_name"}

POST /migrations/rename-field
{"collection": "users", "old_field_name": "emailAddress", "new_field_name": "email"}
```

### Pattern 2: Add Status System

```bash
# Add status with default
POST /migrations/add-field
{"collection": "users", "field_name": "status", "default_value": "active"}

# Add timestamps
POST /migrations/add-field
{"collection": "users", "field_name": "created_at", "default_value": null}
```

### Pattern 3: Normalize Names

```bash
# Split full_name into parts
POST /migrations/split-field
{
  "collection": "users",
  "source_field": "full_name",
  "target_fields": ["first_name", "last_name"],
  "separator": " "
}
```

### Pattern 4: Type Cleanup

```bash
# Convert string prices to numbers
POST /migrations/change-field-type
{
  "collection": "products",
  "field_name": "price",
  "target_type": "number"
}

# Convert status to boolean
POST /migrations/change-field-type
{
  "collection": "users",
  "field_name": "is_active",
  "target_type": "boolean",
  "conversion_map": {"yes": true, "no": false}
}
```

---

## ⚡ Response Format

All endpoints return:

```json
{
  "success": true,
  "message": "Operation description",
  "documents_affected": 1234,
  "execution_time_ms": 450,
  "details": {
    // Operation-specific details
  }
}
```

---

## ⚠️ Safety Checklist

Before running migrations:

- [ ] Analyze collection structure
- [ ] Run dry-run test
- [ ] Export/backup data
- [ ] Test on sample documents
- [ ] Run during low traffic
- [ ] Monitor execution time

---

## 🎯 Merge Strategies

| Strategy | Use Case           | Example                  |
| -------- | ------------------ | ------------------------ |
| `concat` | Combine strings    | first + last → full name |
| `sum`    | Add numbers        | subtotal + tax → total   |
| `array`  | Create list        | tag1, tag2 → tags[]      |
| `first`  | Use first non-null | Try field1, then field2  |

---

## 🔄 Type Conversions

| From   | To      | Example                      |
| ------ | ------- | ---------------------------- |
| string | number  | "99.99" → 99.99              |
| string | boolean | "yes" → true                 |
| any    | string  | 123 → "123"                  |
| any    | array   | "tag" → ["tag"]              |
| any    | object  | "value" → {"value": "value"} |

---

## 💡 Pro Tips

1. **Use snake_case for field names**

   ```json
   ✅ "full_name"
   ❌ "fullName"
   ```

2. **Analyze before migrating**

   ```bash
   GET /migrations/users/analyze-fields
   ```

3. **Test with dry-run**

   ```bash
   POST /migrations/users/dry-run?operation=...
   ```

4. **One operation at a time**

   - Don't chain complex migrations
   - Validate after each step

5. **Use conversion maps for custom logic**
   ```json
   {
     "conversion_map": {
       "active": true,
       "inactive": false
     }
   }
   ```

---

## 🚨 Destructive Operations

These operations **cannot be undone**:

- ❌ `delete-field` - Permanently removes data
- ⚠️ `change-field-type` - May lose precision
- ⚠️ Type conversions without conversion_map

**Always backup before running these!**

---

## 📈 Performance Guide

| Documents  | Time  | Impact |
| ---------- | ----- | ------ |
| < 1,000    | < 1s  | None   |
| 1k - 10k   | 1-5s  | Low    |
| 10k - 100k | 5-30s | Medium |
| > 100k     | 30s+  | High   |

For large collections:

- Run during off-peak hours
- Monitor database load
- Consider batching

---

## 🔗 Related Endpoints

- Export data: `GET /collections/{id}/export`
- Import data: `POST /collections/{id}/import`
- Get schema: `GET /collections/{id}/query/schema`
- Analyze fields: `GET /migrations/{id}/analyze-fields`
