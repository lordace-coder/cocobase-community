# Relationship Detection Flowchart

## 🔄 The Decision Tree

```
User requests: populate=field_name
        ↓
Extract field_name (e.g., "products", "referred_by", "followers")
        ↓
Pluralize field_name
    - products → products
    - referred_by → referred_bys
    - follower → followers
        ↓
┌───────────────────────────────────────────┐
│ Is pluralized name in system collections? │
│ ["users", "app_users", "appusers"]        │
└───────────────────────────────────────────┘
        ↓
    ┌───┴───┐
   YES     NO
    ↓       ↓
┌───────┐ ┌────────────────────────────────┐
│AppUser│ │ Look for collection with name  │
└───────┘ └────────────────────────────────┘
           ↓
       ┌───┴───┐
      FOUND  NOT FOUND
        ↓       ↓
   ┌────────┐ ┌───────┐
   │Document│ │AppUser│
   └────────┘ └───────┘
```

---

## 📊 Real Examples

### Example 1: `populate=products`

```
products → Pluralize → "products"
    ↓
Is "products" in ["users", "app_users", "appusers"]? NO
    ↓
Look for collection named "products"
    ↓
FOUND collection "products" ✓
    ↓
Query: SELECT * FROM documents
       WHERE collection_id = 'products-collection-id'
```

**Result:** ✅ Returns product documents

---

### Example 2: `populate=referred_by`

```
referred_by → Pluralize → "referred_bys"
    ↓
Is "referred_bys" in ["users", "app_users", "appusers"]? NO
    ↓
Look for collection named "referred_bys"
    ↓
NOT FOUND ✗
    ↓
Fallback to AppUser table
    ↓
Query: SELECT * FROM app_users
       WHERE id = '...' AND client_id = '...'
```

**Result:** ✅ Returns user who referred this user

---

### Example 3: `populate=followers` (Ambiguous Case)

**Case A: No "followers" collection**

```
followers → Pluralize → "followers"
    ↓
Is "followers" in system list? NO
    ↓
Look for collection named "followers"
    ↓
NOT FOUND ✗
    ↓
Fallback to AppUser
    ↓
Query: SELECT * FROM app_users WHERE id IN (...)
```

**Result:** ✅ Returns follower users

---

**Case B: "followers" collection exists**

```
followers → Pluralize → "followers"
    ↓
Is "followers" in system list? NO
    ↓
Look for collection named "followers"
    ↓
FOUND ✓
    ↓
Query: SELECT * FROM documents WHERE collection_id='followers-coll-id'
```

**Result:** ⚠️ Returns documents from "followers" collection (might be wrong!)

---

## 🎯 The Three Types of Relationships

### Type 1: Always AppUser (System Collections)

```
Field names that resolve to AppUser:
- users
- app_users
- appusers

These are HARDCODED and will ALWAYS query app_users table.
```

**Example:**

```json
{
  "admin_user_id": "user-123"
}
```

`populate=admin_user` → pluralize to "admin_users" → Not in system list → Try collection → If not found → AppUser

---

### Type 2: Always Collection (When Collection Exists)

```
If a collection with matching name exists:
→ ALWAYS uses that collection
→ NEVER checks AppUser table
```

**Example:**

```json
// Collection "products" exists
{
  "favorite_product_ids": ["prod-1", "prod-2"]
}
```

`populate=favorite_product` → pluralize to "favorite_products" → Not in system list → Look for "favorite_products" or "products" collection → FOUND → Use collection

---

### Type 3: Fallback to AppUser (When Collection Not Found)

```
If NO collection with matching name exists:
→ Falls back to app_users table
```

**Example:**

```json
// No collection named "managers" or "manager"
{
  "manager_id": "user-456"
}
```

`populate=manager` → pluralize to "managers" → Not in system list → Look for "managers" collection → NOT FOUND → Fallback to AppUser

---

## 🔧 How Collections Are Found

The system tries THREE variations:

```
1. Exact name match
   "products" → Look for collection named "products"

2. Singular form (if ends with 's')
   "products" → Try "product"

3. Plural form (if doesn't end with 's')
   "product" → Try "products"
```

**Code from `_get_collection_by_name()`:**

```python
# Try exact name
collection = find(name)

# Try singular
if not found and name.endswith("s"):
    collection = find(name[:-1])  # "products" → "product"

# Try plural
if not found and not name.endswith("s"):
    collection = find(name + "s")  # "product" → "products"

# If still not found → Fallback to AppUser
```

---

## 💡 Tips for Naming

### ✅ Good Practice: Be Explicit

```json
{
  // User relationships - prefix with "user"
  "follower_user_ids": ["user-1", "user-2"],
  "manager_user_id": "user-3",
  "referred_by_user_id": "user-4",

  // Collection relationships - use collection name
  "product_ids": ["prod-1"],
  "order_ids": ["order-1"],
  "team_doc_ids": ["team-1"]
}
```

### ❌ Bad Practice: Ambiguous Names

```json
{
  "followers": ["..."], // Users or documents?
  "related": ["..."], // Users or documents?
  "linked": ["..."] // Users or documents?
}
```

---

## 📝 Quick Reference

| Field Name    | Pluralized     | System Collection? | Collection Exists? | Result                  |
| ------------- | -------------- | ------------------ | ------------------ | ----------------------- |
| `users`       | `users`        | ✅ YES             | -                  | AppUser                 |
| `products`    | `products`     | ❌ NO              | ✅ YES             | Document (products)     |
| `referred_by` | `referred_bys` | ❌ NO              | ❌ NO              | AppUser (fallback)      |
| `followers`   | `followers`    | ❌ NO              | ❌ NO              | AppUser (fallback)      |
| `followers`   | `followers`    | ❌ NO              | ✅ YES             | Document (followers) ⚠️ |
| `manager`     | `managers`     | ❌ NO              | ❌ NO              | AppUser (fallback)      |
| `team`        | `teams`        | ❌ NO              | ✅ YES             | Document (teams)        |

---

## 🎯 Summary

**Detection Order:**

1. Check if in system collections list → AppUser
2. Check if collection exists → Document
3. Fallback → AppUser

**Key Point:**
Collections are checked BEFORE AppUser fallback, so if a collection with that name exists, it will ALWAYS use it (even if you meant AppUser).

**Solution:**
Use explicit naming to avoid conflicts!
