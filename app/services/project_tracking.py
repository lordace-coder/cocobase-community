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
import logging


# Sync to database every N requests (configurable)
SYNC_THRESHOLD = 10  # Sync to DB every 10 requests
REDIS_SYNC_KEY_SUFFIX = ":last_sync"

# Cache plan info to avoid repeated DB queries
_plan_cache = {}
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.models.user import User
import redis
from app.services.redis_worker import get_redis_instance
from app.models.pricing import ApiUsageCounter, get_current_plan
from app.services.email import notify_limit_reached, notify_limit_warning
import logging


# Sync to database every N requests (configurable)
SYNC_THRESHOLD = 10  # Sync to DB every 10 requests
REDIS_SYNC_KEY_SUFFIX = ":last_sync"

# Cache plan info to avoid repeated DB queries
_plan_cache = {}
_plan_cache_ttl = {}
PLAN_CACHE_SECONDS = 300  # 5 minutes


logger = logging.getLogger(__name__)


async def check_and_increment_api_usage(
    project, db: Session, bg: BackgroundTasks, user: User
) -> bool:
    """
    Optimized: Check API limit using Redis with minimal DB hits.
    Redis = fast counter, Database = source of truth
    """
    logger.debug(
        "API usage check called for project: %s",
        project.id if hasattr(project, "id") else "unknown",
    )

    # OPTIMIZATION 1: Cache plan lookups (plans rarely change)
    plan = _get_cached_plan(project, db)

    # Unlimited requests - fast exit
    if plan.max_requests_per_month is None or plan.max_requests_per_month == 0:
        logger.info(
            "Project %s has unlimited plan (max_requests=%s), skipping tracking",
            project.id,
            plan.max_requests_per_month,
        )
        return True

    current_month = datetime.now(timezone.utc).strftime("%Y-%m")
    redis_key = f"api_usage:{project.id}:{current_month}"
    redis_sync_key = f"{redis_key}{REDIS_SYNC_KEY_SUFFIX}"

    try:
        redis_client = get_redis_instance()

        # Get current usage first
        current_usage_str = await redis_client.get(redis_key)

        # Then increment
        new_usage_bytes = await redis_client.incr(redis_key)
        try:
            new_usage = int(new_usage_bytes) if new_usage_bytes is not None else 1
        except Exception:
            new_usage = 1

        # Get sync key
        last_sync = await redis_client.get(redis_sync_key)
        if isinstance(last_sync, bytes):
            last_sync = last_sync.decode("utf-8")

        # Initialize Redis from DB only if needed
        if current_usage_str is None:
            # First access - load from DB and update Redis
            current_usage = await _load_usage_from_db(
                project.id, current_month, db, redis_client, redis_key
            )
            new_usage = current_usage + 1
            await redis_client.set(redis_key, new_usage)
            await redis_client.expire(redis_key, 60 * 60 * 24 * 60)

        current_usage = new_usage - 1  # value before increment

        # Hard limit check AFTER getting the incremented value
        if plan.max_requests_per_month and new_usage > plan.max_requests_per_month:
            if getattr(project, "active", True):
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

        # Set expiry on first increment and schedule initial sync
        if new_usage == 1:
            await redis_client.expire(redis_key, 60 * 60 * 24 * 60)
            logger.info(
                "First request of the month - syncing to DB immediately for project %s",
                project.id,
            )
            bg.add_task(_sync_usage_to_db, project.id, current_month, new_usage, db)

        # Batch sync checks
        last_sync_count = 0
        if last_sync:
            try:
                last_sync_count = int(last_sync)
            except Exception:
                last_sync_count = 0

        if new_usage - last_sync_count >= SYNC_THRESHOLD:
            bg.add_task(_sync_usage_to_db, project.id, current_month, new_usage, db)
            await redis_client.set(redis_sync_key, new_usage)
            await redis_client.expire(redis_sync_key, 60 * 60 * 24 * 60)

        # Notifications
        _send_usage_notifications_optimized(
            new_usage, plan.max_requests_per_month, bg, user, project
        )

        return True

    except redis.ConnectionError as e:
        logger.warning("Redis unavailable, using database: %s", e)
        return _check_api_usage_db_only(project, db, bg, user, plan)

    except Exception as e:
        logger.exception("Error in API usage check: %s", e)
        try:
            logger.debug(
                "Attempting database fallback for project %s",
                project.id if hasattr(project, "id") else "unknown",
            )
            return _check_api_usage_db_only(project, db, bg, user, plan)
        except Exception as fallback_error:
            logger.exception("Database fallback also failed: %s", fallback_error)
            return True


def _get_cached_plan(project, db: Session):
    """
    Cache plan data (not SQLAlchemy objects) to avoid repeated DB queries.
    """
    now = datetime.now(timezone.utc).timestamp()
    cache_key = project.id

    if cache_key in _plan_cache:
        if now - _plan_cache_ttl.get(cache_key, 0) < PLAN_CACHE_SECONDS:
            return _plan_cache[cache_key]

    plan = get_current_plan(project, db)

    plan_data = {
        "max_requests_per_month": plan.max_requests_per_month,
        "id": plan.id if hasattr(plan, "id") else None,
        "name": plan.name if hasattr(plan, "name") else None,
    }

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
    """
    usage_record = (
        db.query(ApiUsageCounter)
        .filter(
            ApiUsageCounter.project_id == project_id, ApiUsageCounter.month == month
        )
        .first()
    )

    if usage_record:
        current_usage = usage_record.request_count
        await redis_client.set(redis_key, current_usage)
        await redis_client.set(f"{redis_key}{REDIS_SYNC_KEY_SUFFIX}", current_usage)
        await redis_client.expire(redis_key, 60 * 60 * 24 * 60)
        await redis_client.expire(
            f"{redis_key}{REDIS_SYNC_KEY_SUFFIX}", 60 * 60 * 24 * 60
        )
        logger.info(
            "Restored usage from DB: %s - %s requests", project_id, current_usage
        )
        return current_usage
    else:
        await redis_client.set(redis_key, 0)
        await redis_client.set(f"{redis_key}{REDIS_SYNC_KEY_SUFFIX}", 0)
        await redis_client.expire(redis_key, 60 * 60 * 24 * 60)
        await redis_client.expire(
            f"{redis_key}{REDIS_SYNC_KEY_SUFFIX}", 60 * 60 * 24 * 60
        )

        new_record = ApiUsageCounter(
            project_id=project_id, month=month, request_count=0
        )
        db.add(new_record)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            return await _load_usage_from_db(
                project_id, month, db, redis_client, redis_key
            )

        return 0


def _sync_usage_to_db(project_id: str, month: str, current_count: int, db: Session):
    """
    Background task to sync Redis counter to database.
    """
    try:
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
        logger.info("Synced usage to DB: %s - %s requests", project_id, current_count)

    except Exception as e:
        logger.exception("Failed to sync usage to DB: %s", e)
        db.rollback()


def _check_api_usage_db_only(
    project, db: Session, bg: BackgroundTasks, user: User, plan
) -> bool:
    """
    Fallback: Use database directly when Redis is unavailable.
    """
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")

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

    if plan.max_requests_per_month and current_usage >= plan.max_requests_per_month:
        if getattr(project, "active", True):
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
    Only send notifications at exact thresholds.
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
    logger.warning("LIMIT REACHED: %s - %s: %s", project.name, resource_type, limit)


def notify_limit_warning(
    user: User,
    project,
    resource_type: str,
    current_usage: int,
    limit: int,
    severity: str,
):
    """Send warning notification."""
    percentage = (current_usage / limit) * 100 if limit else 0
    emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(severity, "")
    logger.info(
        "%s %s: %s - %s: %s/%s (%.0f%%)",
        emoji,
        severity.upper(),
        project.name,
        resource_type,
        current_usage,
        limit,
        percentage,
    )
