# EOFError Diagnosis & Solution

## Problem
You're getting an `EOFError: Ran out of input` when querying the `projects` table. This happens when SQLAlchemy tries to unpickle data from a bytea column but encounters corrupted or incomplete pickle data.

## Root Cause
Your models have been updated to use `ARRAY(String)` for:
- `projects.allowed_origins`
- `app_users.roles`

However, **the database schema hasn't been updated yet**. The database columns are still `bytea` (PickleType) and contain pickled binary data that SQLAlchemy can't properly deserialize.

## Solution - 3 Steps

### Step 1: Check Current Status
Run this inside your Docker container to see the current state:

```bash
# Check database schema
python3 check_schema.py

# This will show:
# - Current alembic migration version
# - Column data types (bytea vs ARRAY)
# - Sample data to identify the problem
```

### Step 2: Run Alembic Migrations
The migrations are already created and will:
1. Create new ARRAY columns
2. Migrate pickled data to arrays
3. Drop old columns and rename new ones

```bash
# Inside your Docker container:
alembic upgrade head
```

Expected output:
```
INFO  [alembic.runtime.migration] Running upgrade ... -> d201486f3935, migrating user roles
✅ Migrated user xxx: ['admin']
INFO  [alembic.runtime.migration] Running upgrade d201486f3935 -> a9ef5fd16185, migrating project allowed url
✅ Migrated project xxx: ['http://localhost:3000']
```

### Step 3: Verify & Restart
```bash
# Verify migrations worked
python3 check_schema.py

# Should now show ARRAY instead of bytea

# Restart your application
docker-compose restart <service-name>
```

## Alternative: Manual Migration (if Alembic fails)

If the Alembic migrations fail due to corrupted data, use the manual migration script:

```bash
# Inside Docker container:
python3 migrate.py fix-all
```

This will:
- Convert all pickled data to PostgreSQL arrays
- Handle corrupted data by resetting to empty arrays
- Update both `app_users.roles` and `projects.allowed_origins`

**Note:** You'll still need to update the column types manually after this:

```sql
-- Run these SQL commands if manual migration was used
ALTER TABLE app_users
  ALTER COLUMN roles TYPE text[]
  USING CASE
    WHEN roles IS NULL THEN '{}'::text[]
    ELSE roles::text[]
  END;

ALTER TABLE projects
  ALTER COLUMN allowed_origins TYPE text[]
  USING CASE
    WHEN allowed_origins IS NULL THEN '{}'::text[]
    ELSE allowed_origins::text[]
  END;
```

## Common Issues

### Issue: Alembic says "already at head"
**Solution:** The migrations may have been partially applied. Check with:
```bash
alembic current
alembic history
```

### Issue: Migrations fail with pickle errors
**Solution:** Use the manual migration script first, then run alembic.

### Issue: Error persists after migration
**Possible causes:**
1. Application wasn't restarted (old code cached)
2. Different database being used (check DATABASE_URL)
3. Multiple instances connecting to old database

## Prevention

To avoid this in the future:
1. Always run migrations before deploying model changes
2. Test migrations on staging database first
3. Use Alembic's `--sql` flag to preview changes
4. Avoid PickleType for production databases (use JSON/JSONB or ARRAY instead)
