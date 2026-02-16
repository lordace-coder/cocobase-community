from datetime import datetime, timezone, timedelta
from app.models.pricing import PricingPlan, ProjectSubscription
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

logger = logging.getLogger(__name__)
def auto_downgrade_expired_projects(db: Session):
    logger.info("Starting expired subscription check...")

    free_plan = (
        db.query(PricingPlan)
        .filter(PricingPlan.is_free.is_(True))
        .first()
    )
    if not free_plan:
        raise ValueError("Free plan not found!")

    now = datetime.now(timezone.utc)

    # Get all paid subscriptions (not free plan)
    paid_subs = (
        db.query(ProjectSubscription)
        .filter(
            ProjectSubscription.end_date.isnot(None),
            ProjectSubscription.plan_id != free_plan.id,
        )
        .all()
    )

    logger.info(f"Found {len(paid_subs)} paid subscriptions to evaluate")

    expired_count = 0
    downgraded = 0

    for sub in paid_subs:
        grace_days = sub.grace_period_days or 0
        end_date = sub.end_date

        # Normalize datetime safely
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        grace_end = end_date + timedelta(days=grace_days)

        logger.debug(
            f"Project {sub.project_id} | "
            f"end={end_date}, grace_end={grace_end}, now={now}, is_active={sub.is_active}"
        )

        # Check if subscription has expired (past end_date)
        if now >= end_date and sub.is_active:
            # Mark as inactive immediately after expiry
            sub.is_active = False
            expired_count += 1
            logger.info(f"Marking subscription for project {sub.project_id} as inactive (expired)")

        # Check if grace period has ended - downgrade to free plan
        if now >= grace_end and sub.plan_id != free_plan.id:
            sub.plan_id = free_plan.id
            sub.is_active = True  # Reactivate with free plan
            sub.end_date = None  # Free plan has no expiry
            downgraded += 1
            logger.info(f"Downgrading project {sub.project_id} to free plan (grace period ended)")

    if expired_count or downgraded:
        db.commit()
        logger.info(f"✓ Marked {expired_count} subscriptions as inactive, downgraded {downgraded} projects to free plan")
    else:
        logger.info("✓ No subscriptions need updating")

    return downgraded
