from datetime import datetime
from app.models.pricing import PricingPlan, ProjectSubscription


def auto_downgrade_expired_projects(db):
    free_plan = db.query(PricingPlan).filter_by(name="Free").first()
    if not free_plan:
        raise ValueError("Free plan not found!")

    expired_subs = (
        db.query(ProjectSubscription)
        .filter(
            ProjectSubscription.end_date != None,
            ProjectSubscription.end_date < datetime.utcnow(),
            ProjectSubscription.auto_renew == False,
        )
        .all()
    )

    for sub in expired_subs:
        sub.plan_id = free_plan.id
        sub.is_active = True
        db.add(sub)

    db.commit()
    print(f"Downgraded {len(expired_subs)} projects to Free plan.")
