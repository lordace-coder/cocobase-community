# Schema Migrations - Quick Start

## 🚀 Getting Started in 5 Minutes

### Step 1: Analyze Your Collection

```bash
curl -X GET "https://api.cocobase.com/migrations/users/analyze-fields" \
  -H "Authorization: Bearer YOUR_API_KEY"
```

**Output:**

```json
{
  "collection": "users",
  "total_documents": 1000,
  "fields": {
    "fullName": { "present_in": 1000 },
    "emailAddress": { "present_in": 1000 }
  }
}
```

---

### Step 2: Test with Dry Run

```bash
curl -X POST "https://api.cocobase.com/migrations/users/dry-run?operation=rename-field" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "old_field_name": "fullName",
    "new_field_name": "full_name"
  }'
```

**Output:**

```json
{
  "estimated_affected": 1000,
  "sample_changes": [
    {
      "document_id": "1",
      "before": { "fullName": "John Doe" },
      "after": { "full_name": "John Doe" }
    }
  ],
  "warning": "This is a dry run. No changes were made."
}
```

---

### Step 3: Execute Migration

```bash
curl -X POST "https://api.cocobase.com/migrations/rename-field" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "collection": "users",
    "old_field_name": "fullName",
    "new_field_name": "full_name"
  }'
```

**Output:**

```json
{
  "success": true,
  "message": "Field 'fullName' renamed to 'full_name' in 1000 documents",
  "documents_affected": 1000,
  "execution_time_ms": 250
}
```

---

## 🎯 Most Common Operations

### 1. Rename a Field

```bash
POST /migrations/rename-field
{
  "collection": "users",
  "old_field_name": "fullName",
  "new_field_name": "full_name"
}
```

### 2. Add a Field

```bash
POST /migrations/add-field
{
  "collection": "users",
  "field_name": "status",
  "default_value": "active"
}
```

### 3. Convert Type

```bash
POST /migrations/change-field-type
{
  "collection": "products",
  "field_name": "price",
  "target_type": "number"
}
```

### 4. Merge Fields

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

---

## 📝 Complete Example: Normalize Users Collection

```bash
# 1. Analyze
curl -X GET "/migrations/users/analyze-fields"

# 2. Rename inconsistent fields
curl -X POST "/migrations/rename-field" \
  -d '{"collection": "users", "old_field_name": "fullName", "new_field_name": "full_name"}'

curl -X POST "/migrations/rename-field" \
  -d '{"collection": "users", "old_field_name": "emailAddress", "new_field_name": "email"}'

# 3. Add status system
curl -X POST "/migrations/add-field" \
  -d '{"collection": "users", "field_name": "status", "default_value": "active"}'

# 4. Convert booleans
curl -X POST "/migrations/change-field-type" \
  -d '{
    "collection": "users",
    "field_name": "is_active",
    "target_type": "boolean",
    "conversion_map": {"yes": true, "no": false}
  }'

# 5. Delete legacy fields
curl -X POST "/migrations/delete-field" \
  -d '{"collection": "users", "field_name": "legacy_id"}'
```

---

## 🐍 Python Quick Start

```python
import requests

API_KEY = "your-api-key"
BASE_URL = "https://api.cocobase.com"
HEADERS = {"Authorization": f"Bearer {API_KEY}"}

# Analyze
response = requests.get(
    f"{BASE_URL}/migrations/users/analyze-fields",
    headers=HEADERS
)
print(response.json())

# Rename field
response = requests.post(
    f"{BASE_URL}/migrations/rename-field",
    headers=HEADERS,
    json={
        "collection": "users",
        "old_field_name": "fullName",
        "new_field_name": "full_name"
    }
)
print(response.json())
```

---

## ⚠️ Safety First!

### Always Do This:

1. **Analyze first** - Know your data structure
2. **Dry run** - Test before executing
3. **Backup** - Export data before destructive operations
4. **One at a time** - Don't chain operations
5. **Verify** - Check results after each operation

### Never Do This:

- ❌ Skip dry run for important data
- ❌ Delete fields without backup
- ❌ Run multiple operations without verification
- ❌ Change types without conversion maps
- ❌ Migrate during peak traffic

---

## 📚 Learn More

- **Full Guide:** `SCHEMA_MIGRATIONS_GUIDE.md`
- **Quick Reference:** `SCHEMA_MIGRATIONS_QUICK_REF.md`
- **Python Examples:** `examples/schema_migrations.py`
- **Summary:** `SCHEMA_MIGRATIONS_SUMMARY.md`

---

## 🆘 Common Issues

### Issue: "Collection not found"

**Solution:** Use collection name or ID, not display name

### Issue: "Field doesn't exist"

**Solution:** Run analyze first to see actual field names

### Issue: "Type conversion failed"

**Solution:** Use conversion_map for custom mappings

### Issue: "Too slow"

**Solution:** Run during low traffic, or batch by filtering

---

## ✅ You're Ready!

Start with:

```bash
GET /migrations/YOUR_COLLECTION/analyze-fields
```

Then choose your operation and go! 🚀
