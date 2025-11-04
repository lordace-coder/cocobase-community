# Performance Optimization Guide

## Current Performance Issues

### 1. **AppUser Model**

- ❌ `data` column is `JSON` type (not `JSONB`)
- ❌ No indexes on commonly queried JSONB fields
- ❌ No index on `created_at` for sorting
- ❌ Each populate query does individual lookups (N+1 problem)

### 2. **Document Model**

- ✅ Already has GIN index on `data` (GOOD!)
- ✅ Uses `JSONB` type (GOOD!)
- ✅ Has index on `collection_id` (GOOD!)
- ⚠️ No specific indexes for commonly queried fields

---

## Recommended Optimizations

### Phase 1: Database Schema Improvements (High Impact)

#### 1.1 Change AppUser.data from JSON to JSONB

**Why:** JSONB supports indexing, faster queries, and PostgreSQL operators
**Impact:** 3-10x faster JSONB queries

```sql
-- Migration: Change JSON to JSONB
ALTER TABLE app_users
ALTER COLUMN data TYPE JSONB USING data::jsonb;
```

#### 1.2 Add GIN Index on AppUser.data

**Why:** Enables fast searches on any JSONB field
**Impact:** 10-100x faster for JSONB queries

```sql
-- Add GIN index for general JSONB queries
CREATE INDEX ix_app_users_data_gin
ON app_users USING gin (data jsonb_path_ops);
```

#### 1.3 Add Specific JSONB Field Indexes

**Why:** Even faster for commonly queried fields
**Impact:** 5-50x faster for specific field queries

```sql
-- Index for referred_by (most common relationship)
CREATE INDEX ix_app_users_referred_by
ON app_users ((data->>'referred_by'));

-- Index for email verification status
CREATE INDEX ix_app_users_email_verified
ON app_users ((data->>'is_email_verified'));

-- Index for role
CREATE INDEX ix_app_users_role
ON app_users ((data->>'role'));

-- Index for phone number
CREATE INDEX ix_app_users_phone
ON app_users ((data->>'phone_number'));
```

#### 1.4 Add Sorting Indexes

**Why:** Fast ORDER BY queries
**Impact:** 10-100x faster sorting

```sql
-- Index for created_at sorting (most common)
CREATE INDEX ix_app_users_created_at
ON app_users (created_at DESC);

-- Index for created_at in JSONB data (if using data.created_at)
CREATE INDEX ix_app_users_data_created_at
ON app_users ((data->>'created_at') DESC);
```

#### 1.5 Composite Indexes for Common Queries

**Why:** Optimize frequent query patterns
**Impact:** 5-20x faster for combined filters

```sql
-- For queries filtering by project + referred_by
CREATE INDEX ix_app_users_client_referred
ON app_users (client_id, (data->>'referred_by'));

-- For queries filtering by project + email verification
CREATE INDEX ix_app_users_client_verified
ON app_users (client_id, (data->>'is_email_verified'));

-- For queries filtering by project + role
CREATE INDEX ix_app_users_client_role
ON app_users (client_id, (data->>'role'));
```

#### 1.6 Add Index for Document Sorting

**Why:** Fast ORDER BY on documents
**Impact:** 10-50x faster sorting

```sql
-- Index for created_at sorting on documents
CREATE INDEX ix_documents_created_at
ON documents (created_at DESC);

-- Composite index for collection + created_at
CREATE INDEX ix_documents_collection_created
ON documents (collection_id, created_at DESC);
```

---

### Phase 2: Code Optimizations (Medium Impact)

#### 2.1 Batch Loading for Relationships (Fix N+1)

**Current Problem:** Each populate does individual queries
**Solution:** Use batch loading

```python
# Instead of:
for user_dict in users_data:
    related_user = db.query(AppUser).filter(AppUser.id == related_id).first()

# Do:
all_related_ids = [user["data"]["referred_by"] for user in users_data if user["data"].get("referred_by")]
related_users = db.query(AppUser).filter(AppUser.id.in_(all_related_ids)).all()
related_users_map = {user.id: user for user in related_users}
```

**Status:** ✅ Already implemented in `UserRelationshipHelper`!

#### 2.2 Add Query Result Caching

**Why:** Avoid repeated identical queries
**Impact:** 100-1000x faster for repeated queries

```python
from functools import lru_cache
from cachetools import TTLCache
import hashlib

# Add to your code
query_cache = TTLCache(maxsize=1000, ttl=60)  # 60 second cache

def get_cache_key(query_params):
    return hashlib.md5(str(sorted(query_params.items())).encode()).hexdigest()
```

#### 2.3 Use Select Load for Large Result Sets

**Why:** Only load fields you need
**Impact:** 2-5x faster, less memory

```python
# Instead of loading all columns:
query = db.query(AppUser)

# Load only needed columns:
from sqlalchemy import select
query = db.query(AppUser.id, AppUser.email, AppUser.data, AppUser.created_at)
```

#### 2.4 Add Connection Pooling Configuration

**Why:** Reuse database connections
**Impact:** 2-10x faster query execution

```python
# In database.py, configure pool:
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,          # Number of connections to keep
    max_overflow=40,       # Max additional connections
    pool_pre_ping=True,    # Verify connections before use
    pool_recycle=3600,     # Recycle connections after 1 hour
)
```

---

### Phase 3: Query Optimizations (Low-Hanging Fruit)

#### 3.1 Limit Default Page Size

**Current:** No default limit (could load millions)
**Recommendation:** Default to 50, max 1000

```python
limit = min(int(query_params.get("limit", 50)), 1000)
```

#### 3.2 Avoid COUNT(\*) for Large Tables

**Why:** COUNT is slow on large tables
**Solution:** Use estimated counts or skip for pagination

```python
# Instead of:
total = query.count()  # Slow!

# Use:
if offset == 0:
    total = query.count()
else:
    total = -1  # Don't count on subsequent pages
```

#### 3.3 Add Query Timeout

**Why:** Prevent slow queries from blocking
**Impact:** Better overall system performance

```python
from sqlalchemy import text
db.execute(text("SET statement_timeout = '30s'"))
```

---

## Implementation Priority

### 🔴 **Critical (Do First)**

1. Change AppUser.data to JSONB
2. Add GIN index on AppUser.data
3. Add index on referred_by field
4. Add created_at indexes

### 🟡 **Important (Do Soon)**

5. Add composite indexes for common queries
6. Configure connection pooling
7. Add default query limits

### 🟢 **Nice to Have**

8. Add query caching
9. Optimize COUNT queries
10. Add query timeouts

---

## SQL Migration Script

```sql
-- ============================================
-- COCOBASE Performance Optimization Migration
-- ============================================

-- 1. Change JSON to JSONB (CRITICAL)
ALTER TABLE app_users
ALTER COLUMN data TYPE JSONB USING data::jsonb;

-- 2. Add GIN index for general JSONB operations (CRITICAL)
CREATE INDEX CONCURRENTLY ix_app_users_data_gin
ON app_users USING gin (data jsonb_path_ops);

-- 3. Add specific field indexes (HIGH PRIORITY)
CREATE INDEX CONCURRENTLY ix_app_users_referred_by
ON app_users ((data->>'referred_by'))
WHERE data->>'referred_by' IS NOT NULL;

CREATE INDEX CONCURRENTLY ix_app_users_email_verified
ON app_users ((data->>'is_email_verified'));

CREATE INDEX CONCURRENTLY ix_app_users_role
ON app_users ((data->>'role'));

CREATE INDEX CONCURRENTLY ix_app_users_phone
ON app_users ((data->>'phone_number'))
WHERE data->>'phone_number' IS NOT NULL;

-- 4. Add sorting indexes (HIGH PRIORITY)
CREATE INDEX CONCURRENTLY ix_app_users_created_at
ON app_users (created_at DESC);

CREATE INDEX CONCURRENTLY ix_documents_created_at
ON documents (created_at DESC);

-- 5. Add composite indexes (MEDIUM PRIORITY)
CREATE INDEX CONCURRENTLY ix_app_users_client_referred
ON app_users (client_id, (data->>'referred_by'))
WHERE data->>'referred_by' IS NOT NULL;

CREATE INDEX CONCURRENTLY ix_app_users_client_verified
ON app_users (client_id, (data->>'is_email_verified'));

CREATE INDEX CONCURRENTLY ix_documents_collection_created
ON documents (collection_id, created_at DESC);

-- 6. Analyze tables to update statistics
ANALYZE app_users;
ANALYZE documents;
ANALYZE collections;

-- ============================================
-- Verification Queries
-- ============================================

-- Check index sizes
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_indexes
JOIN pg_class ON pg_indexes.indexname = pg_class.relname
WHERE schemaname = 'public'
    AND tablename IN ('app_users', 'documents', 'collections')
ORDER BY pg_relation_size(indexrelid) DESC;

-- Check if JSONB conversion succeeded
SELECT
    column_name,
    data_type
FROM information_schema.columns
WHERE table_name = 'app_users'
    AND column_name = 'data';
-- Should show: jsonb

-- Test query performance (before/after comparison)
EXPLAIN ANALYZE
SELECT * FROM app_users
WHERE client_id = 'your-project-id'
    AND data->>'referred_by' IS NOT NULL
ORDER BY created_at DESC
LIMIT 50;
```

---

## Expected Performance Improvements

### Before Optimization

- List 1000 users: **500-2000ms**
- Filter by referred_by: **1000-5000ms**
- Populate relationships: **2000-10000ms** (N+1 problem)
- Complex filters: **5000-30000ms**

### After Optimization

- List 1000 users: **50-200ms** (10x faster)
- Filter by referred_by: **20-100ms** (50x faster)
- Populate relationships: **100-500ms** (20x faster)
- Complex filters: **100-1000ms** (30x faster)

---

## Model Updates Required

Update your models to use JSONB:

```python
# app/models/app_client.py
from sqlalchemy.dialects.postgresql import JSONB

class AppUser(Base):
    __tablename__ = "app_users"
    # ... other fields ...

    # Change from JSON to JSONB
    data = Column(JSONB, nullable=True, default=dict)  # Changed from JSON

    # Add table args for index
    __table_args__ = (
        UniqueConstraint("client_id", "email", name="uq_client_email"),
        Index(
            "ix_app_users_data_gin",
            "data",
            postgresql_using="gin",
            postgresql_ops={"data": "jsonb_path_ops"},
        ),
    )
```

---

## Monitoring & Benchmarking

### Add Query Logging

```python
import logging
import time

def log_slow_queries(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start

        if duration > 1.0:  # Log queries over 1 second
            logging.warning(f"Slow query: {func.__name__} took {duration:.2f}s")

        return result
    return wrapper
```

### PostgreSQL Slow Query Log

```sql
-- Enable slow query logging
ALTER SYSTEM SET log_min_duration_statement = 1000;  -- Log queries > 1s
ALTER SYSTEM SET log_statement = 'all';
SELECT pg_reload_conf();
```

---

## Load Testing

Use these scripts to test improvements:

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test list users endpoint
ab -n 1000 -c 10 "http://localhost:8000/api/auth-collections/users?limit=50"

# Test with filters
ab -n 500 -c 5 "http://localhost:8000/api/auth-collections/users?data.referred_by_isnull=false&populate=referred_by&limit=50"
```

---

## Summary

**Total Impact:** 10-50x performance improvement for most queries

**Effort Required:**

- SQL migration: 10 minutes (run the script)
- Model updates: 5 minutes (change JSON to JSONB)
- Code optimizations: Already done! (batch loading)

**Quick Win:** Just run the SQL migration script - most improvements are automatic!
