# Database Sequence Protection

## Problem

If you encounter this error:
```
(psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint "tablename_pkey"
DETAIL: Key (id)=(X) already exists.
```

This means your PostgreSQL sequence is out of sync with the actual data in your table.

## Solution

### Automatic Protection (Already Active!)

The application has **automatic sequence protection** that prevents this issue:

```bash
# Verify protection is active
.venv/bin/python verify_triggers.py
```

### If You Need to Re-setup

If triggers were dropped or you're setting up a new database:

```bash
# Run setup to create all protection triggers
.venv/bin/python setup_sequence_protection.py
```

This will:
1. Fix all current sequence issues
2. Create database triggers that automatically fix sequences after any insert
3. Verify everything is working

**Result**: Duplicate key errors are prevented automatically! 🎉

## How It Works

The system has three layers of protection:

1. **Database Triggers**: Run after every INSERT to keep sequences in sync
2. **Startup Check**: Application checks sequences on startup
3. **Sequence Manager**: Python module that manages everything automatically

### For Developers

When you add a new table with an auto-incrementing ID, the protection is **automatic** - no configuration needed!

## Test Protection

```bash
.venv/bin/python test_sequence_protection.py
```

## Troubleshooting

If you see duplicate key errors:

1. **Check triggers**:
   ```bash
   .venv/bin/python verify_triggers.py
   ```

2. **Re-run setup**:
   ```bash
   .venv/bin/python setup_sequence_protection.py
   ```

## Technical Details

**Problem**: When you manually INSERT with an explicit ID, PostgreSQL doesn't update the sequence. Next auto-insert tries to use an ID that already exists.

**Solution**: Database triggers automatically update sequences after every insert, keeping them in sync.

---

**Files**:
- `app/core/sequence_manager.py` - Core implementation
- `app/main.py` - Startup integration
- `setup_sequence_protection.py` - Setup script
- `verify_triggers.py` - Verification tool
- `test_sequence_protection.py` - Test suite
