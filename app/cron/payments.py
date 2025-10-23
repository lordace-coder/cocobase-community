from datetime import datetime, timezone, timedelta
from app.models.pricing import PricingPlan, ProjectSubscription
from sqlalchemy.orm import Session
from sqlalchemy import and_


def auto_downgrade_expired_projects(db: Session):
    """
    Downgrade expired projects to free plan after grace period ends.
    Should be run as a scheduled task (e.g., daily cron job).
    """
    # Get free plan
    free_plan = db.query(PricingPlan).filter(PricingPlan.is_free == True).first()
    if not free_plan:
        raise ValueError("Free plan not found!")

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

    downgraded_count = 0
    for sub in expired_subs:
        # Check if grace period has ended
        grace_end = sub.end_date + timedelta(days=sub.grace_period_days)

        # Make grace_end timezone-aware if needed
        if grace_end.tzinfo is None:
            grace_end = grace_end.replace(tzinfo=timezone.utc)

        if now > grace_end:
            # Downgrade to free plan
            sub.plan_id = free_plan.id
            sub.is_active = True
            sub.end_date = None  # Free plans don't expire
            db.add(sub)
            downgraded_count += 1

            # TODO: Log or notify
            print(f"Downgraded project {sub.project_id} to Free plan")

    # Commit all changes at once
    if downgraded_count > 0:
        db.commit()
        print(f"Downgraded {downgraded_count} projects to Free plan.")
    else:
        print("No projects to downgrade.")

    return downgraded_count
