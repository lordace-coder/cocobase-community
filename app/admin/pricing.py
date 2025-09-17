from sqladmin import ModelView
from app.models.pricing import PricingPlan,ProjectSubscription






class PricingPlanModel(ModelView,model = PricingPlan):
    pass


class ProjectSubscriptionModel(ModelView,model = ProjectSubscription):
    pass