from sqladmin import ModelView
from app.models.pricing import ApiUsageCounter, PricingPlan, ProjectSubscription, Payment


class PricingPlanModel(ModelView, model=PricingPlan):
    column_list = [PricingPlan.name, PricingPlan.price,PricingPlan.max_storage_mb,PricingPlan.max_users]
    pass


class ProjectSubscriptionModel(ModelView, model=ProjectSubscription):
    pass


class ApiUsageCounterModel(ModelView, model=ApiUsageCounter):
    pass


class PaymentModel(ModelView, model=Payment):
    name = "Payment"
    name_plural = "Payments"
    icon = "fa-solid fa-money-bill"

    column_list = [
        Payment.id,
        Payment.reference,
        Payment.amount,
        Payment.currency,
        Payment.status,
        Payment.provider,
        Payment.created_at,
        Payment.paid_at,
    ]

    column_details_list = [
        Payment.id,
        Payment.reference,
        Payment.provider,
        Payment.amount,
        Payment.currency,
        Payment.status,
        Payment.project_id,
        Payment.user_id,
        Payment.plan_id,
        Payment.subscription_id,
        Payment.payment_metadata,
        Payment.provider_response,
        Payment.webhook_received,
        Payment.webhook_received_at,
        Payment.paid_at,
        Payment.created_at,
        Payment.updated_at,
    ]

    column_searchable_list = [Payment.reference]
    column_sortable_list = [Payment.created_at, Payment.amount, Payment.status, Payment.paid_at]
    column_default_sort = [(Payment.created_at, True)]

    # Format amount display with Naira symbol
    column_formatters = {
        Payment.amount: lambda m, a: f"₦{m.amount:,.2f}"
    }

    # Allow create, edit, delete
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True