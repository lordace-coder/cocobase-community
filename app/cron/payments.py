from datetime import datetime, timezone, timedelta
from app.models.pricing import PricingPlan, ProjectSubscription
from sqlalchemy.orm import Session
from sqlalchemy import and_
import logging

logger = logging.getLogger(__name__)


def auto_downgrade_expired_projects(db: Session):
    """
    Downgrade expired projects to free plan after grace period ends.

    This function is automatically run daily at 2:00 AM UTC by the scheduler.
    It can also be triggered manually via the /cron/check-subscriptions endpoint.

    Args:
        db: Database session

    Returns:
        int: Number of projects downgraded
    """
    logger.info("Starting expired subscription check...")

    # Get free plan
    free_plan = db.query(PricingPlan).filter(PricingPlan.is_free == True).first()
    if not free_plan:
        logger.error("Free plan not found in database!")
        raise ValueError("Free plan not found!")

    logger.info(f"Free plan found: {free_plan.name} (ID: {free_plan.id})")

    # Use timezone-aware datetime
    now = datetime.now(timezone.utc)

    # Find subscriptions that are:
    # 1. Past their end date + grace period
    # 2. Not set to auto-renew
    # 3. Not already on free plan
    # 4. Currently active (to avoid processing already downgraded ones)
    expired_subs = (
        db.query(ProjectSubscription)
        .filter(
            and_(
                ProjectSubscription.end_date != None,
                ProjectSubscription.auto_renew == False,
                ProjectSubscription.is_active == True,
                ProjectSubscription.plan_id != free_plan.id,  # Not already free
            )
        )
        .all()
    )

    logger.info(f"Found {len(expired_subs)} subscriptions to check")

    downgraded_count = 0
    for sub in expired_subs:
        # Check if grace period has ended
        grace_end = sub.end_date + timedelta(days=sub.grace_period_days)

        # Make grace_end timezone-aware if needed
        if grace_end.tzinfo is None:
            grace_end = grace_end.replace(tzinfo=timezone.utc)

        if now > grace_end:
            # Downgrade to free plan
            logger.info(
                f"Downgrading project {sub.project_id}: "
                f"grace period ended at {grace_end}"
            )

            sub.plan_id = free_plan.id
            sub.is_active = True
            sub.end_date = None  # Free plans don't expire
            db.add(sub)
            downgraded_count += 1

            # TODO: Send email notification to project owner
        else:
            days_remaining = (grace_end - now).days
            logger.debug(
                f"Project {sub.project_id} still in grace period "
                f"({days_remaining} days remaining)"
            )

    # Commit all changes at once
    if downgraded_count > 0:
        db.commit()
        logger.info(f"✓ Successfully downgraded {downgraded_count} projects to Free plan")
    else:
        logger.info("✓ No projects to downgrade")

    return downgraded_count
