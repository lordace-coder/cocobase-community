from sqladmin import ModelView
from app.models.pricing import PricingPlan, ProjectSubscription


class PricingPlanModel(ModelView, model=PricingPlan):
    column_list = [PricingPlan.name, PricingPlan.price,PricingPlan.max_storage_mb,PricingPlan.max_users]
    pass


class ProjectSubscriptionModel(ModelView, model=ProjectSubscription):
    pass
