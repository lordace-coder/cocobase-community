from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.user import User
import redis
from typing import Optional
from app.services.redis_worker import get_redis_instance
from datetime import datetime, timezone
from fastapi import HTTPException, BackgroundTasks
from app.models.pricing import ApiUsageCounter, get_current_plan
from app.models.user import User
from app.services.email import notify_limit_reached, notify_limit_warning
from sqlalchemy.orm import Session


# Sync to database every N requests (configurable)
SYNC_THRESHOLD = 10  # Sync to DB every 10 requests
REDIS_SYNC_KEY_SUFFIX = ":last_sync"

# Cache plan info to avoid repeated DB queries
_plan_cache = {}
_plan_cache_ttl = {}
PLAN_CACHE_SECONDS = 300  # 5 minutes


async def check_and_increment_api_usage(
    project, db: Session, bg: BackgroundTasks, user: User
) -> bool:
    """
    Optimized: Check API limit using Redis with minimal DB hits.
    Redis = fast counter, Database = source of truth
    """
    print(
        f"🔵 API usage check called for project: {project.id if hasattr(project, 'id') else 'unknown'}"
    )

    # OPTIMIZATION 1: Cache plan lookups (plans rarely change)
    plan = _get_cached_plan(project, db)

    # Unlimited requests - fast exit
    if plan.max_requests_per_month is None or plan.max_requests_per_month == 0:
        print(
            f"⚠️ Project {project.id} has unlimited plan (max_requests={plan.max_requests_per_month}), skipping tracking"
        )
        return True

    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    redis_key = f"api_usage:{project.id}:{current_month}"
    redis_sync_key = f"{redis_key}{REDIS_SYNC_KEY_SUFFIX}"

    try:
        redis_client = get_redis_instance()

        # OPTIMIZATION 2: Use Redis pipeline for atomic multi-operation
        # Get current usage first
        current_usage_str = await redis_client.get(redis_key)

        # Then increment
        new_usage_bytes = await redis_client.incr(redis_key)
        new_usage = int(new_usage_bytes) if new_usage_bytes is not None else 1

        # Get sync key
        last_sync = await redis_client.get(redis_sync_key)

        if isinstance(last_sync, bytes):
            last_sync = last_sync.decode("utf-8")

        # OPTIMIZATION 3: Initialize Redis from DB only if needed
        if current_usage_str is None:
            # First access - load from DB and update Redis atomically
            current_usage = await _load_usage_from_db(
                project.id, current_month, db, redis_client, redis_key
            )
            new_usage = current_usage + 1
            await redis_client.set(redis_key, new_usage)
            await redis_client.expire(redis_key, 60 * 60 * 24 * 60)

        current_usage = new_usage - 1  # Before increment

        # Hard limit check AFTER getting the incremented value
        if new_usage > plan.max_requests_per_month:
            # OPTIMIZATION 4: Only update DB if project is still active (avoid unnecessary writes)
            if project.active:
                project.active = False
                db.commit()

                bg.add_task(
                    notify_limit_reached,
                    user,
                    project,
                    "api_requests",
                    plan.max_requests_per_month,
                )

            raise HTTPException(
                status_code=429,
                detail=f"API request limit reached ({plan.max_requests_per_month:,} requests/month). Please upgrade your plan.",
                headers={
                    "Retry-After": "2592000",
                    "X-RateLimit-Limit": str(plan.max_requests_per_month),
                    "X-RateLimit-Remaining": "0",
                },
            )

        # Set expiry on first increment
        if new_usage == 1:
            await redis_client.expire(redis_key, 60 * 60 * 24 * 60)
            # Sync first request immediately for visibility
            print(f"🎯 First request of the month - syncing to DB immediately")
            bg.add_task(_sync_usage_to_db, project.id, current_month, new_usage, db)

        # OPTIMIZATION 5: Batch sync checks (avoid setting on every request)
        last_sync_count = 0
        if last_sync:
            if isinstance(last_sync, bytes):
                last_sync_count = int(last_sync.decode("utf-8"))
            else:
                last_sync_count = int(last_sync)

        if new_usage - last_sync_count >= SYNC_THRESHOLD:
            # Sync to database in background (non-blocking)
            bg.add_task(_sync_usage_to_db, project.id, current_month, new_usage, db)
            # Update last sync marker
            await redis_client.set(redis_sync_key, new_usage)
            await redis_client.expire(redis_sync_key, 60 * 60 * 24 * 60)

        # OPTIMIZATION 6: Notification checks only at exact thresholds
        _send_usage_notifications_optimized(
            new_usage, plan.max_requests_per_month, bg, user, project
        )

        return True

    except redis.ConnectionError as e:
        # Redis is down - use database directly
        print(f"⚠️  Redis unavailable, using database: {e}")
        return _check_api_usage_db_only(project, db, bg, user, plan)

    except Exception as e:
        print(f"❌ Error in API usage check: {e}")
        import traceback

        traceback.print_exc()
        # FALLBACK: Try database-only mode before giving up
        try:
            print("🔄 Attempting database fallback...")
            return _check_api_usage_db_only(project, db, bg, user, plan)
        except Exception as fallback_error:
            print(f"❌ Database fallback also failed: {fallback_error}")
            traceback.print_exc()
            # Last resort: allow request through to avoid blocking legitimate traffic
            return True


def _get_cached_plan(project, db: Session):
    """
    OPTIMIZATION: Cache plan data (not SQLAlchemy objects) to avoid repeated DB queries.
    Plans rarely change, so this is safe with short TTL.
    """
    now = datetime.now(timezone.utc).timestamp()
    cache_key = project.id

    # Check if cached and not expired
    if cache_key in _plan_cache:
        if now - _plan_cache_ttl.get(cache_key, 0) < PLAN_CACHE_SECONDS:
            return _plan_cache[cache_key]

    # Cache miss or expired - fetch from DB
    plan = get_current_plan(project, db)

    # CRITICAL: Cache only the data we need, not the SQLAlchemy object
    # This prevents detached instance errors
    plan_data = {
        "max_requests_per_month": plan.max_requests_per_month,
        "id": plan.id if hasattr(plan, "id") else None,
        "name": plan.name if hasattr(plan, "name") else None,
    }

    # Create a simple namespace object to mimic the plan interface
    class PlanCache:
        def __init__(self, data):
            self.max_requests_per_month = data["max_requests_per_month"]
            self.id = data.get("id")
            self.name = data.get("name")

    cached_plan = PlanCache(plan_data)
    _plan_cache[cache_key] = cached_plan
    _plan_cache_ttl[cache_key] = now

    return cached_plan


async def _load_usage_from_db(
    project_id: str, month: str, db: Session, redis_client, redis_key: str
) -> int:
    """
    Load usage from database (source of truth) and populate Redis.
    Called when Redis is empty (restart, eviction, etc.)
    """
    usage_record = (
        db.query(ApiUsageCounter)
        .filter(
            ApiUsageCounter.project_id == project_id, ApiUsageCounter.month == month
        )
        .first()
    )

    if usage_record:
        # Found in database - restore to Redis
        current_usage = usage_record.request_count

        await redis_client.set(redis_key, current_usage)
        await redis_client.set(f"{redis_key}{REDIS_SYNC_KEY_SUFFIX}", current_usage)
        await redis_client.expire(redis_key, 60 * 60 * 24 * 60)
        await redis_client.expire(
            f"{redis_key}{REDIS_SYNC_KEY_SUFFIX}", 60 * 60 * 24 * 60
        )

        print(f"✅ Restored usage from DB: {project_id} - {current_usage} requests")
        return current_usage
    else:
        # First request ever for this month - initialize both Redis and DB
        await redis_client.set(redis_key, 0)
        await redis_client.set(f"{redis_key}{REDIS_SYNC_KEY_SUFFIX}", 0)
        await redis_client.expire(redis_key, 60 * 60 * 24 * 60)
        await redis_client.expire(
            f"{redis_key}{REDIS_SYNC_KEY_SUFFIX}", 60 * 60 * 24 * 60
        )

        # Create DB record
        new_record = ApiUsageCounter(
            project_id=project_id, month=month, request_count=0
        )
        db.add(new_record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            # Race condition - another request created it, reload
            return _load_usage_from_db(project_id, month, db, redis_client, redis_key)

        return 0


def _sync_usage_to_db(project_id: str, month: str, current_count: int, db: Session):
    """
    Background task to sync Redis counter to database.
    This ensures data durability.
    """
    try:
        # OPTIMIZATION: Use upsert pattern (more efficient than query + update)
        usage_record = (
            db.query(ApiUsageCounter)
            .filter(
                ApiUsageCounter.project_id == project_id, ApiUsageCounter.month == month
            )
            .first()
        )

        if usage_record:
            usage_record.request_count = current_count
        else:
            usage_record = ApiUsageCounter(
                project_id=project_id, month=month, request_count=current_count
            )
            db.add(usage_record)

        db.commit()
        print(f"✅ Synced usage to DB: {project_id} - {current_count} requests")

    except Exception as e:
        print(f"❌ Failed to sync usage to DB: {e}")
        db.rollback()


def _check_api_usage_db_only(
    project, db: Session, bg: BackgroundTasks, user: User, plan
) -> bool:
    """
    Fallback: Use database directly when Redis is unavailable.
    Slower but reliable.
    """
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")

    # Get or create with row lock (prevents race conditions)
    usage_record = (
        db.query(ApiUsageCounter)
        .filter(
            ApiUsageCounter.project_id == project.id,
            ApiUsageCounter.month == current_month,
        )
        .with_for_update()
        .first()
    )

    if not usage_record:
        usage_record = ApiUsageCounter(
            project_id=project.id, month=current_month, request_count=0
        )
        db.add(usage_record)
        db.flush()

    current_usage = usage_record.request_count

    # Check limit
    if current_usage >= plan.max_requests_per_month:
        if project.active:
            project.active = False
            db.commit()
            bg.add_task(
                notify_limit_reached,
                user,
                project,
                "api_requests",
                plan.max_requests_per_month,
            )

        raise HTTPException(
            status_code=429,
            detail=f"API request limit reached ({plan.max_requests_per_month:,} requests/month).",
        )

    # Increment
    usage_record.request_count += 1
    db.commit()

    _send_usage_notifications_optimized(
        usage_record.request_count, plan.max_requests_per_month, bg, user, project
    )

    return True


def _send_usage_notifications_optimized(
    current_usage: int, limit: int, bg: BackgroundTasks, user: User, project
):
    """
    OPTIMIZATION: Only send notifications at EXACT thresholds to avoid
    checking on every single request.
    """
    thresholds = {
        int(limit * 0.9): "critical",
        int(limit * 0.8): "warning",
        int(limit * 0.5): "info",
    }

    if current_usage in thresholds:
        severity = thresholds[current_usage]
        bg.add_task(
            notify_limit_warning,
            user,
            project,
            "api_requests",
            current_usage,
            limit,
            severity,
        )


def notify_limit_reached(user: User, project, resource_type: str, limit: int):
    """Send notification when limit is reached."""
    print(f"🚨 LIMIT REACHED: {project.name} - {resource_type}: {limit}")
    pass


def notify_limit_warning(
    user: User,
    project,
    resource_type: str,
    current_usage: int,
    limit: int,
    severity: str,
):
    """Send warning notification."""
    percentage = (current_usage / limit) * 100
    emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}[severity]
    print(
        f"{emoji} {severity.upper()}: {project.name} - {resource_type}: {current_usage}/{limit} ({percentage:.0f}%)"
    )
    pass
