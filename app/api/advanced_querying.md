# Advanced Query Filtering Guide

## 🎯 Quick Reference

### Basic Operators

| Operator     | Usage              | Example                       | SQL Equivalent                   |
| ------------ | ------------------ | ----------------------------- | -------------------------------- |
| `eq`         | Equals (default)   | `status=active`               | `status = 'active'`              |
| `ne`         | Not equals         | `status_ne=deleted`           | `status != 'deleted'`            |
| `gt`         | Greater than       | `age_gt=18`                   | `age > 18`                       |
| `gte`        | Greater or equal   | `age_gte=18`                  | `age >= 18`                      |
| `lt`         | Less than          | `age_lt=65`                   | `age < 65`                       |
| `lte`        | Less or equal      | `age_lte=65`                  | `age <= 65`                      |
| `contains`   | Contains substring | `name_contains=john`          | `name ILIKE '%john%'`            |
| `startswith` | Starts with        | `name_startswith=john`        | `name ILIKE 'john%'`             |
| `endswith`   | Ends with          | `email_endswith=gmail.com`    | `email ILIKE '%gmail.com'`       |
| `in`         | In list            | `status_in=active,pending`    | `status IN ('active','pending')` |
| `notin`      | Not in list        | `status_notin=deleted,banned` | `status NOT IN (...)`            |
| `isnull`     | Is null/not null   | `deletedAt_isnull=true`       | `deletedAt IS NULL`              |

---

## 📚 Query Examples by Use Case

### 1️⃣ **Simple AND Conditions** (Default Behavior)

All parameters without special prefixes are ANDed together.

```bash
# Find active users aged 18-65
GET /collections/users/documents?status=active&age_gte=18&age_lte=65

# SQL: WHERE status = 'active' AND age >= 18 AND age <= 65
```

```bash
# Find verified premium users in USA
GET /collections/users/documents?isVerified=true&isPremium=true&country=USA

# SQL: WHERE isVerified = true AND isPremium = true AND country = 'USA'
```

---

### 2️⃣ **Multi-Field OR** (Same Value, Multiple Fields)

Search for the same value across multiple fields using `field1__or__field2`.

```bash
# Search "john" in name OR email
GET /collections/users/documents?name__or__email_contains=john

# SQL: WHERE (name ILIKE '%john%' OR email ILIKE '%john%')
```

```bash
# Find documents where firstName OR lastName is "Smith"
GET /collections/users/documents?firstName__or__lastName=Smith

# SQL: WHERE (firstName = 'Smith' OR lastName = 'Smith')
```

```bash
# Search in multiple fields with operator
GET /collections/users/documents?name__or__username__or__email_contains=admin

# SQL: WHERE (name ILIKE '%admin%' OR username ILIKE '%admin%' OR email ILIKE '%admin%')
```

---

### 3️⃣ **Simple OR Conditions** (Using `[or]` Prefix)

Group multiple conditions with OR logic using the `[or]` prefix.

```bash
# Find users who are EITHER over 18 OR admins
GET /collections/users/documents?[or]age_gte=18&[or]role=admin

# SQL: WHERE (age >= 18 OR role = 'admin')
```

```bash
# Find premium users OR verified users
GET /collections/users/documents?[or]isPremium=true&[or]isVerified=true

# SQL: WHERE (isPremium = true OR isVerified = true)
```

```bash
# Find high priority OR overdue tasks
GET /collections/tasks/documents?[or]priority=high&[or]status=overdue

# SQL: WHERE (priority = 'high' OR status = 'overdue')
```

---

### 4️⃣ **Mixed AND + OR Conditions**

Combine AND and OR logic. OR conditions are grouped, then ANDed with other filters.

```bash
# Find active users who are EITHER premium OR verified
GET /collections/users/documents?status=active&[or]isPremium=true&[or]isVerified=true

# SQL: WHERE status = 'active' AND (isPremium = true OR isVerified = true)
```

```bash
# Find incomplete tasks assigned to user OR high priority, sorted by date
GET /collections/tasks/documents?status=incomplete&assignedTo=user123&[or]priority_gte=8&[or]dueDate_lt=2025-01-01

# SQL: WHERE status = 'incomplete' AND assignedTo = 'user123'
#      AND (priority >= 8 OR dueDate < '2025-01-01')
```

```bash
# Find products in stock AND (on sale OR new arrivals)
GET /collections/products/documents?inStock=true&[or]onSale=true&[or]isNew=true

# SQL: WHERE inStock = true AND (onSale = true OR isNew = true)
```

---

### 5️⃣ **Multiple OR Groups** (Named Groups)

Create separate OR groups using `[or:groupname]` syntax. Each group is ORed internally, groups are ANDed together.

```bash
# (age >= 18 OR role = admin) AND (country = USA OR country = UK)
GET /collections/users/documents?[or:age]age_gte=18&[or:age]role=admin&[or:country]country=USA&[or:country]country=UK

# SQL: WHERE (age >= 18 OR role = 'admin')
#      AND (country = 'USA' OR country = 'UK')
```

```bash
# (premium OR verified) AND (active OR pending)
GET /collections/users/documents?[or:tier]isPremium=true&[or:tier]isVerified=true&[or:status]status=active&[or:status]status=pending

# SQL: WHERE (isPremium = true OR isVerified = true)
#      AND (status = 'active' OR status = 'pending')
```

```bash
# Complex product search: (in stock OR pre-order) AND (on sale OR discounted) AND price <= 100
GET /collections/products/documents?[or:availability]inStock=true&[or:availability]isPreOrder=true&[or:deals]onSale=true&[or:deals]hasDiscount=true&price_lte=100

# SQL: WHERE (inStock = true OR isPreOrder = true)
#      AND (onSale = true OR hasDiscount = true)
#      AND price <= 100
```

---

### 6️⃣ **IN Operator** (Multiple Values)

Check if a field matches any value in a comma-separated list.

```bash
# Find users with specific roles
GET /collections/users/documents?role_in=admin,moderator,support

# SQL: WHERE role IN ('admin', 'moderator', 'support')
```

```bash
# Find tasks with multiple statuses
GET /collections/tasks/documents?status_in=todo,in-progress,review

# SQL: WHERE status IN ('todo', 'in-progress', 'review')
```

```bash
# Find products in multiple categories, on sale
GET /collections/products/documents?category_in=electronics,computers,phones&onSale=true

# SQL: WHERE category IN ('electronics', 'computers', 'phones') AND onSale = true
```

---

### 7️⃣ **NULL Checks**

Check if a field is null or not null.

```bash
# Find users who haven't been deleted
GET /collections/users/documents?deletedAt_isnull=true

# SQL: WHERE deletedAt IS NULL
```

```bash
# Find users with a profile picture
GET /collections/users/documents?profilePicture_isnull=false

# SQL: WHERE profilePicture IS NOT NULL
```

```bash
# Find active users with verified email
GET /collections/users/documents?status=active&emailVerifiedAt_isnull=false

# SQL: WHERE status = 'active' AND emailVerifiedAt IS NOT NULL
```

---

### 8️⃣ **String Operations**

Advanced string matching.

```bash
# Find emails from Gmail
GET /collections/users/documents?email_endswith=gmail.com

# SQL: WHERE email ILIKE '%gmail.com'
```

```bash
# Find users whose name starts with "John"
GET /collections/users/documents?name_startswith=John

# SQL: WHERE name ILIKE 'John%'
```

```bash
# Search for "test" in username or email
GET /collections/users/documents?username__or__email_contains=test

# SQL: WHERE (username ILIKE '%test%' OR email ILIKE '%test%')
```

```bash
# Find admin or moderator emails (contains + in)
GET /collections/users/documents?role_in=admin,moderator&email_contains=company.com

# SQL: WHERE role IN ('admin', 'moderator') AND email ILIKE '%company.com%'
```

---

### 9️⃣ **Sorting & Pagination**

Control result ordering and pagination.

```bash
# Sort by age ascending
GET /collections/users/documents?sort=age&order=asc

# Sort by creation date descending (default)
GET /collections/users/documents?sort=created_at&order=desc

# Paginate results (20 per page, skip first 40)
GET /collections/users/documents?limit=20&offset=40

# Combined: Active users, sorted by age, page 2
GET /collections/users/documents?status=active&sort=age&order=asc&limit=20&offset=20
```

---

## 🔥 Real-World Complex Examples

### E-commerce Platform

```bash
# Find available products: (in stock OR pre-order) AND (on sale OR new) AND price 50-200
GET /collections/products/documents?[or:avail]inStock=true&[or:avail]preOrder=true&[or:promo]onSale=true&[or:promo]isNew=true&price_gte=50&price_lte=200&sort=price&order=asc
```

### User Management System

```bash
# Find risky users: (multiple failed logins OR suspicious activity) AND NOT banned
GET /collections/users/documents?[or]failedLogins_gte=5&[or]suspiciousActivity=true&status_ne=banned&sort=lastLogin&order=desc
```

### Task Management

```bash
# Find urgent tasks: (high priority OR overdue) AND (assigned to me OR unassigned) AND NOT completed
GET /collections/tasks/documents?[or:urgency]priority=high&[or:urgency]isOverdue=true&[or:assignment]assignedTo=user123&[or:assignment]assignedTo_isnull=true&status_ne=completed
```

### Social Media

```bash
# Find popular posts: (likes > 100 OR comments > 50) AND created in last week AND NOT reported
GET /collections/posts/documents?[or]likes_gt=100&[or]comments_gt=50&createdAt_gte=2025-01-05&isReported=false&sort=likes&order=desc
```

### Healthcare Records

```bash
# Find critical patients: (fever > 38 OR blood pressure > 140) AND (age > 65 OR has chronic condition)
GET /collections/patients/documents?[or:vitals]temperature_gt=38&[or:vitals]bloodPressure_gt=140&[or:risk]age_gt=65&[or:risk]chronicCondition=true
```

### Inventory Management

```bash
# Find products needing restock: (stock < 10 OR out of stock) AND (popular OR essential) AND NOT discontinued
GET /collections/inventory/documents?[or:low]stock_lt=10&[or:low]stock=0&[or:important]isPopular=true&[or:important]isEssential=true&discontinued=false
```

---

## 🎨 Visual Logic Tree Examples

### Example 1: User Search

```
Query: ?status=active&[or]age_gte=18&[or]role=admin&country=USA

Logic Tree:
└─ AND
   ├─ status = 'active'
   ├─ country = 'USA'
   └─ OR
      ├─ age >= 18
      └─ role = 'admin'

Result: Active USA users who are EITHER 18+ OR admins
```

### Example 2: Product Filter

```
Query: ?[or:avail]inStock=true&[or:avail]preOrder=true&[or:price]onSale=true&[or:price]price_lt=50&category=electronics

Logic Tree:
└─ AND
   ├─ category = 'electronics'
   ├─ OR (availability)
   │  ├─ inStock = true
   │  └─ preOrder = true
   └─ OR (price)
      ├─ onSale = true
      └─ price < 50

Result: Electronics that are (in stock OR pre-order) AND (on sale OR under $50)
```

### Example 3: Complex Task Filter

```
Query: ?status=open&[or:assign]assignedTo=me&[or:assign]assignedTo_isnull=true&[or:priority]priority=high&[or:priority]dueDate_lt=today

Logic Tree:
└─ AND
   ├─ status = 'open'
   ├─ OR (assignment)
   │  ├─ assignedTo = 'me'
   │  └─ assignedTo IS NULL
   └─ OR (priority)
      ├─ priority = 'high'
      └─ dueDate < today

Result: Open tasks (assigned to me OR unassigned) AND (high priority OR overdue)
```

---

## 💡 Best Practices

### ✅ DO's

1. **Use meaningful group names**

   ```bash
   # Good: Clear group names
   ?[or:age]age_gte=18&[or:age]role=admin&[or:location]country=US&[or:location]country=UK

   # Bad: Confusing group names
   ?[or:a]age_gte=18&[or:a]role=admin&[or:b]country=US&[or:b]country=UK
   ```

2. **Combine with sorting for better UX**

   ```bash
   ?status=active&[or]priority=high&[or]isUrgent=true&sort=createdAt&order=desc
   ```

3. **Use IN operator for multiple values**

   ```bash
   # Good
   ?status_in=active,pending,review

   # Bad (multiple parameters)
   ?[or]status=active&[or]status=pending&[or]status=review
   ```

### ❌ DON'Ts

1. **Don't over-complicate queries**

   - If you have more than 3 OR groups, consider simplifying your logic
   - Use the API to do complex filtering, not the client

2. **Don't mix group names confusingly**

   ```bash
   # Bad: Mixing related conditions in different groups
   ?[or:a]age_gte=18&[or:b]age_lte=65

   # Good: Keep related conditions together
   ?age_gte=18&age_lte=65
   ```

3. **Don't forget URL encoding**
   ```bash
   # Special characters must be encoded
   ?name_contains=John%20Doe  # Space = %20
   ?email=user%40example.com  # @ = %40
   ```

---

## 🧪 Testing Your Queries

### Python Example

```python
import requests

base_url = "https://api.example.com/collections/users/documents"

# Simple query
response = requests.get(f"{base_url}?status=active&age_gte=18")

# Complex query
params = {
    "status": "active",
    "[or]isPremium": "true",
    "[or]isVerified": "true",
    "sort": "createdAt",
    "order": "desc",
    "limit": 50
}
response = requests.get(base_url, params=params)
print(response.json())
```

### JavaScript Example

```javascript
const baseUrl = "https://api.example.com/collections/users/documents";

// Build query params
const params = new URLSearchParams({
  status: "active",
  "[or]isPremium": "true",
  "[or]isVerified": "true",
  age_gte: "18",
  sort: "createdAt",
  order: "desc",
});

fetch(`${baseUrl}?${params}`)
  .then((res) => res.json())
  .then((data) => console.log(data));
```

### cURL Example

```bash
# Simple query
curl "https://api.example.com/collections/users/documents?status=active&age_gte=18"

# Complex query with OR groups
curl "https://api.example.com/collections/users/documents?\
[or:tier]isPremium=true&\
[or:tier]isVerified=true&\
[or:location]country=US&\
[or:location]country=UK&\
status=active&\
sort=createdAt&\
order=desc"
```

---

## 🚀 Performance Tips

1. **Index your JSON fields** in PostgreSQL

   ```sql
   CREATE INDEX idx_users_status ON documents USING gin ((data->'status'));
   CREATE INDEX idx_users_age ON documents ((CAST(data->>'age' AS INTEGER)));
   ```

2. **Use pagination** for large result sets

   ```bash
   ?limit=50&offset=0  # First page
   ?limit=50&offset=50 # Second page
   ```

3. **Avoid wildcard searches** on large datasets

   ```bash
   # Slow
   ?name_contains=a

   # Better
   ?name_startswith=john
   ```

4. **Combine filters** to reduce result set early

   ```bash
   # Good: Filter by indexed field first
   ?status=active&name_contains=john

   # Less optimal: Broad search first
   ?name_contains=john&status=active
   ```

---

## 📖 Summary

Your BaaS now supports powerful query capabilities:

- ✅ **12 operators**: eq, ne, gt, gte, lt, lte, contains, startswith, endswith, in, notin, isnull
- ✅ **Boolean logic**: AND (default), OR (using `[or]`), named OR groups (using `[or:name]`)
- ✅ **Multi-field search**: `field1__or__field2_operator=value`
- ✅ **Sorting**: `?sort=field&order=asc/desc`
- ✅ **Pagination**: `?limit=X&offset=Y`

This gives your users Firebase-like querying power with SQL flexibility! 🎉
