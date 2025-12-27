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

    expired_subs = (
        db.query(ProjectSubscription)
        .filter(
            ProjectSubscription.end_date.isnot(None),
            ProjectSubscription.plan_id != free_plan.id,
        )
        .all()
    )

    logger.info(f"Found {len(expired_subs)} subscriptions to evaluate")

    downgraded = 0

    for sub in expired_subs:
        grace_days = sub.grace_period_days or 0
        end_date = sub.end_date

        # Normalize datetime safely
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)

        grace_end = end_date + timedelta(days=grace_days)

        logger.debug(
            f"Project {sub.project_id} | "
            f"end={end_date}, grace_end={grace_end}, now={now}"
        )

        if now >= grace_end:
            sub.plan_id = free_plan.id
            sub.is_active = True
            sub.end_date = None
            downgraded += 1

    if downgraded:
        db.commit()
        logger.info(f"✓ Downgraded {downgraded} projects")
    else:
        logger.info("✓ No projects eligible for downgrade")

    return downgraded
