# How `favorite_product_id` Resolves to `products` Collection

## 🔍 Step-by-Step Trace

Let's trace **exactly** how `favorite_product_id` resolves to the `products` collection:

---

## Starting Point

You have data like this:

```json
{
  "id": "user-123",
  "favorite_product_id": "prod-456"
}
```

You make a query:

```bash
GET /collections/users?populate=favorite_product
```

---

## The Resolution Process

### Step 1: Field Name Extraction

```python
# From the populate parameter
populate = "favorite_product"
field_name = "favorite_product"
```

**Input:** `favorite_product`

---

### Step 2: Build ID Field Names

```python
# From _populate_single_field() - Line 739
id_field = f"{field_name}_id"      # "favorite_product_id"
ids_field = f"{field_name}_ids"    # "favorite_product_ids"
```

**Generated:**

- Single: `favorite_product_id`
- Multiple: `favorite_product_ids`

---

### Step 3: Pluralize the Field Name

```python
# From _populate_single_field() - Line 743
target_name = self._pluralize(field_name)

# _pluralize() logic - Line 1052
def _pluralize(self, word: str) -> str:
    if word.endswith("y"):
        return word[:-1] + "ies"
    elif word.endswith("s"):
        return word + "es"
    else:
        return word + "s"  # ← This case applies!
```

**Calculation:**

```
Input: "favorite_product"
Ends with "y"? NO
Ends with "s"? NO
Default: Add "s"
Output: "favorite_products"
```

**Result:** `favorite_product` → `favorite_products`

---

### Step 4: Check if System Collection

```python
# From _populate_single_field() - Line 744
is_user_relation = self._is_system_collection(target_name)

# _is_system_collection() - Line 542
SYSTEM_COLLECTIONS = {
    "users": AppUser,
    "app_users": AppUser,
    "appusers": AppUser,
}

def _is_system_collection(self, collection_name: str) -> bool:
    return collection_name.lower() in self.SYSTEM_COLLECTIONS
```

**Check:**

```
Is "favorite_products" in ["users", "app_users", "appusers"]? NO
```

**Result:** `is_user_relation = False`

---

### Step 5: Fetch Related Document

Since `is_user_relation = False`, it calls:

```python
# From _populate_single_field() - Line 751
related = self._fetch_related_document(
    target_name,      # "favorite_products"
    project_id,       # Current project
    doc[id_field],    # "prod-456"
    nested_populates
)
```

---

### Step 6: Get Collection by Name

```python
# From _fetch_related_document() - Line 810
collection = self._get_collection_by_name(collection_name, project_id)
```

Now the magic happens in `_get_collection_by_name()`:

```python
# Line 1000-1048
def _get_collection_by_name(self, name: str, project_id: str):
    # name = "favorite_products"

    # Try 1: Exact match
    collection = db.query(Collection).filter(
        Collection.name == "favorite_products",  # ← Try this first
        Collection.project_id == project_id
    ).first()

    # Result: NOT FOUND (no collection named "favorite_products")

    # Try 2: Singular form (name ends with "s")
    if not collection and name.endswith("s"):
        singular_name = self._singularize(name)
        # _singularize("favorite_products") → "favorite_product"

        collection = db.query(Collection).filter(
            Collection.name == "favorite_product",  # ← Try singular
            Collection.project_id == project_id
        ).first()

    # Result: STILL NOT FOUND (no collection named "favorite_product")

    # BUT WAIT! The system is actually smarter...
```

---

### Step 7: The Actual Smart Lookup

Actually, looking at the code more carefully, here's what happens:

```python
# The system doesn't just look for "favorite_products"
# It extracts the BASE collection name

# From the field name pattern:
"favorite_product_id" → Base name is "product"

# The system looks for:
1. "favorite_products" (pluralized full name)
2. "favorite_product" (singular full name)
3. BUT the collection is actually named "products"

# How does it find "products"?
```

---

## 🤔 Wait... It Doesn't!

**Actually, you're right to be confused!**

Looking at the code, `favorite_product_id` would look for:

1. Collection named `favorite_products`
2. Collection named `favorite_product` (singular)

**It would NOT automatically find `products` collection!**

---

## ✅ What Actually Works

For the system to find the `products` collection, you need to name your fields like this:

### Option 1: Match Collection Name Exactly

```json
{
  "product_id": "prod-456", // ← Resolves to "products"
  "product_ids": ["prod-1", "prod-2"]
}
```

**Populate:** `populate=product`

**Resolution:**

```
product → pluralize → "products" → Find collection "products" ✓
```

---

### Option 2: Use Plural Form

```json
{
  "products_id": "prod-456", // ← Also works
  "products_ids": ["prod-1"]
}
```

**Populate:** `populate=products`

**Resolution:**

```
products → already plural → Find collection "products" ✓
```

---

### Option 3: Use Descriptor with Matching Base

```json
{
  "liked_product_ids": ["prod-1"] // ← Works!
}
```

**Populate:** `populate=liked_product`

**Resolution:**

```
liked_product → pluralize → "liked_products"
    ↓
Try "liked_products" → NOT FOUND
    ↓
Try singular "liked_product" → NOT FOUND
    ↓
❌ Would fail to find "products"
```

**So this DOESN'T work automatically!**

---

## 🎯 The Truth

### What Works:

```json
{
  // Field name base MUST match collection name
  "product_id": "prod-1", // product → products ✓
  "team_id": "team-1", // team → teams ✓
  "category_id": "cat-1" // category → categories ✓
}
```

### What Doesn't Work:

```json
{
  // These DON'T automatically find base collections
  "favorite_product_id": "prod-1", // Looks for "favorite_products" ✗
  "liked_product_id": "prod-1", // Looks for "liked_products" ✗
  "saved_product_id": "prod-1" // Looks for "saved_products" ✗
}
```

---

## 💡 The Solution

If you want to use descriptive names, you need to create collections that match:

### Approach 1: Create Matching Collections

```json
// Create collection named "favorite_products"
{
  "id": "fav-1",
  "collection": "favorite_products",
  "data": {
    "product_id": "prod-456",
    "user_id": "user-123"
  }
}

// Then you can use:
{
  "favorite_product_id": "fav-1"
}
```

---

### Approach 2: Store Base Collection IDs

```json
{
  // Just use the base collection name
  "product_id": "prod-456", // ← Direct reference
  "favorite": true, // ← Add metadata
  "liked_at": "2024-01-01"
}
```

**Populate:** `populate=product` ✓

---

### Approach 3: Use Array for Categories

```json
{
  // Group by relationship type
  "favorite_product_ids": ["prod-1", "prod-2"],
  "saved_product_ids": ["prod-3"],
  "recent_product_ids": ["prod-4"]
}
```

Then populate: `populate=favorite_product`

But this looks for `favorite_products` collection, not `products`!

---

## 📋 The Actual Algorithm

```
Given: populate=favorite_product

Step 1: Pluralize
  favorite_product → favorite_products

Step 2: Look for collection
  Query: SELECT * FROM collections
         WHERE name = 'favorite_products' AND project_id = ?

Step 3: If not found, try singular
  Query: SELECT * FROM collections
         WHERE name = 'favorite_product' AND project_id = ?

Step 4: If still not found
  Fallback to AppUser table

NO STEP extracts "product" from "favorite_product" automatically!
```

---

## ✅ Summary

**To make `favorite_product_id` work with `products` collection:**

**Option 1:** Just use `product_id`

```json
{ "product_id": "prod-456" }
```

**Option 2:** Create a `favorite_products` collection

```sql
INSERT INTO collections (name, project_id)
VALUES ('favorite_products', 'proj-123');
```

**Option 3:** Store favorites in products with metadata

```json
{
  "product_id": "prod-456",
  "is_favorite": true,
  "favorited_at": "2024-01-01"
}
```

**The system does NOT automatically extract base collection names from prefixes!**
