# How Relationship Detection Actually Works

## 🎯 The Current Implementation

The system uses the **`AutoRelationshipResolver`** class to automatically detect whether a relationship points to:

- **AppUser** (system users)
- **Collection Document** (your custom collections)

---

## 🔍 Detection Strategy

### Step-by-Step Process

When you use `populate=products` or `populate=referred_by`, here's what happens:

```
1. Field name extraction
   populate=products → field_name = "products"
   populate=referred_by → field_name = "referred_by"

2. Pluralize the field name
   products → products (already plural)
   referred_by → referred_bys (pluralized)

3. Check if it's a SYSTEM collection
   IF pluralized name in ["users", "app_users", "appusers"]:
      → It's an AppUser relationship
   ELSE:
      → Try to find a collection with that name

4. Look for the ID field in data
   products → Look for "products_id" or "products_ids" in doc.data
   referred_by → Look for "referred_by_id" or "referred_by_ids" in doc.data

5. Query the appropriate source
   IF system collection:
      → Query AppUser table
   ELSE:
      → Query Documents table filtered by collection_id
```

---

## 💡 The Magic: System Collections List

```python
# From utilities.py line ~490
SYSTEM_COLLECTIONS = {
    "users": AppUser,
    "app_users": AppUser,
    "appusers": AppUser,
}
```

**This is the key!** These are hardcoded "special" collection names that map to the AppUser model.

---

## 📊 Examples Explained

### Example 1: `products` (Collection)

```json
{
  "id": "user-123",
  "data": {
    "liked_products": ["prod-1", "prod-2"]
  }
}
```

**Query:** `populate=liked_products`

**Detection Flow:**

```
1. Field: "liked_products"
2. Pluralize: "liked_products" → "liked_products"
3. Is system collection? NO (not in ["users", "app_users", "appusers"])
4. Look for collection named "liked_products" or "liked_product"
5. Found collection "products" ✓
6. Query: SELECT * FROM documents WHERE collection_id='products-collection-id' AND id IN ('prod-1', 'prod-2')
```

---

### Example 2: `referred_by` (AppUser)

```json
{
  "id": "user-123",
  "data": {
    "referred_by_id": "user-456"
  }
}
```

**Query:** `populate=referred_by`

**Detection Flow:**

```
1. Field: "referred_by"
2. Pluralize: "referred_by" → "referred_bys"
3. Is system collection? NO (not in ["users", "app_users", "appusers"])
4. Look for collection named "referred_bys" or "referred_by"
5. NOT FOUND ✗
6. Fallback: Try AppUser table
7. Query: SELECT * FROM app_users WHERE id='user-456' AND client_id='project-id'
```

---

### Example 3: `followers` (AppUser)

```json
{
  "id": "user-123",
  "data": {
    "follower_ids": ["user-456", "user-789"]
  }
}
```

**Query:** `populate=followers`

**Detection Flow:**

```
1. Field: "followers"
2. Pluralize: "followers" → "followers" (already plural)
3. Is system collection? NO (not in list)
4. Look for collection named "followers"
5. If NOT found → Try AppUser table
6. Query: SELECT * FROM app_users WHERE id IN ('user-456', '789') AND client_id='project-id'
```

---

## ⚠️ The Problem

### What if you have BOTH?

```
Scenario:
- Collection named "followers" (for tracking relationships)
- AppUser relationships also named "followers_ids"
```

**What happens:**

```
1. populate=followers
2. System looks for collection "followers"
3. FOUND collection "followers" ✓
4. Returns documents from "followers" collection
5. NEVER checks AppUser table ❌
```

**Result:** Wrong data returned!

---

## ✅ Current Workarounds

### Option 1: Use Different Names

```json
// For AppUser relationships
{
  "follower_user_ids": ["user-1", "user-2"],  // ← Add "user" prefix
  "following_user_ids": ["user-3"]
}

// For collection documents
{
  "product_ids": ["prod-1"],
  "team_ids": ["team-1"]
}
```

---

### Option 2: Avoid Collection Name Conflicts

**Don't create collections named:**

- `users`, `app_users`, `appusers` (reserved)
- Any name that might match user relationships

**Good names:**

- `products`, `orders`, `posts` ← Clear collection names
- `teams`, `categories`, `articles`

**Bad names (ambiguous):**

- `followers`, `friends` ← Could be users OR documents
- `members`, `owners` ← Ambiguous

---

### Option 3: Explicit Type Naming

```json
// Make it obvious in the field name
{
  "follower_user_ids": ["user-1"], // ← Clearly users
  "favorite_product_ids": ["prod-1"], // ← Clearly products
  "team_doc_ids": ["team-1"] // ← Clearly documents
}
```

---

## 🔄 The Actual Code Flow

### From `_populate_single_field()` (Line ~669)

```python
def _populate_single_field(self, doc, field_name, project_id, nested_populates):
    """Populate a single relationship field."""

    # Step 1: Build field names
    id_field = f"{field_name}_id"      # e.g., "product_id"
    ids_field = f"{field_name}_ids"    # e.g., "product_ids"

    # Step 2: Pluralize and check if system collection
    target_name = self._pluralize(field_name)  # "product" → "products"
    is_user_relation = self._is_system_collection(target_name)
    #                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #                  Checks if in ["users", "app_users", "appusers"]

    # Step 3: Fetch based on type
    if id_field in doc and doc[id_field]:
        if is_user_relation:
            related = self._fetch_user(doc[id_field], ...)
        else:
            related = self._fetch_related_document(target_name, ...)
```

---

### From `_is_system_collection()` (Line ~542)

```python
SYSTEM_COLLECTIONS = {
    "users": AppUser,
    "app_users": AppUser,
    "appusers": AppUser,
}

def _is_system_collection(self, collection_name: str) -> bool:
    """Check if this is a system collection (like users)."""
    return collection_name.lower() in self.SYSTEM_COLLECTIONS
    #      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #      Returns True ONLY for: users, app_users, appusers
```

---

### From `_get_collection_by_name()` (Line ~880)

```python
def _get_collection_by_name(self, name: str, project_id: str):
    """Get collection - tries both singular and plural forms."""

    # Try exact name first
    collection = db.query(Collection).filter(
        Collection.name == name,
        Collection.project_id == project_id
    ).first()

    # If not found, try singular form
    if not collection and name.endswith("s"):
        singular_name = self._singularize(name)
        collection = db.query(Collection).filter(
            Collection.name == singular_name
        ).first()

    # If not found, try plural form
    if not collection and not name.endswith("s"):
        plural_name = self._pluralize(name)
        collection = db.query(Collection).filter(
            Collection.name == plural_name
        ).first()

    # If STILL not found → Falls back to AppUser
    return collection
```

---

## 📋 Summary

### How It Knows:

1. **Hardcoded List**: System collections = `["users", "app_users", "appusers"]`
2. **Collection Lookup**: Try to find collection with matching name
3. **Fallback**: If no collection found → Try AppUser table

### For `products`:

```
products → Not in system list → Look for "products" collection → Found ✓ → Use collection
```

### For `referred_by`:

```
referred_by → Not in system list → Look for "referred_by" collection → Not found ✗ → Try AppUser ✓
```

### For `followers`:

```
followers → Not in system list → Look for "followers" collection
  ↓
If found → Use collection (might be wrong!)
If not found → Try AppUser
```

---

## 🎯 Best Practice

**To avoid ambiguity:**

1. **Name user relationships explicitly:**

   ```json
   {
     "follower_user_ids": [...],    // ← Clear
     "manager_user_id": "...",
     "referred_by_user_id": "..."
   }
   ```

2. **Name collection relationships clearly:**

   ```json
   {
     "product_ids": [...],          // ← Clear
     "order_ids": [...],
     "team_doc_ids": [...]
   }
   ```

3. **Don't create collections that conflict with user relationship names**

---

**The system works by trying collections first, then falling back to AppUsers!**
