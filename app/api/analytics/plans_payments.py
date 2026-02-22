"""
💳 Plans & Payments Analytics
=============================

Subscription plans, limits, usage, and payment analytics.
"""

from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, case, desc, and_
from sqlalchemy.orm import Session
import json
import io
import csv

from app.core.database import get_db
from app.core.dependencies import require_dashboard_access
from app.models.app_client import Project, AppUser
from app.models.cloud_functions import CloudFunction
from app.models.pricing import (
    ApiUsageCounter,
    Payment,
    ProjectSubscription,
    get_current_plan,
)
from app.storage.storage import get_project_usage

from .common import PlanLimitsAnalytics, PaymentAnalytics, TimeSeriesData

router = APIRouter()


@router.get("/{project_id}/plan-limits", response_model=PlanLimitsAnalytics)
def get_plan_limits_analytics(
    project_id: str,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Get comprehensive plan limits and current usage.

    Returns:
    - Current plan details
    - All resource limits
    - Current usage for each resource
    - Usage percentages
    - Subscription status
    """
    current_month = datetime.now(timezone.utc).strftime("%Y-%m")

    # Get current plan
    plan = get_current_plan(project, db)

    # Get subscription
    subscription = (
        db.query(ProjectSubscription)
        .filter(
            ProjectSubscription.project_id == project_id,
            ProjectSubscription.is_active == True,
        )
        .order_by(ProjectSubscription.start_date.desc())
        .first()
    )

    # OPTIMIZATION: Get all current usage in one query
    usage_stats = (
        db.query(
            func.count(func.distinct(AppUser.id)).label("users"),
            func.count(func.distinct(CloudFunction.id)).label("functions"),
        )
        .select_from(Project)
        .outerjoin(AppUser, AppUser.client_id == project_id)
        .outerjoin(CloudFunction, CloudFunction.project_id == project_id)
        .filter(Project.id == project_id)
        .first()
    )

    current_users = usage_stats.users or 0
    current_functions = usage_stats.functions or 0

    # API requests this month
    api_usage = (
        db.query(ApiUsageCounter.request_count)
        .filter(
            ApiUsageCounter.project_id == project_id,
            ApiUsageCounter.month == current_month,
        )
        .first()
    )
    current_requests = api_usage[0] if api_usage else 0

    current_storage_mb = get_project_usage(project_id) / 1024 / 1024

    # Calculate usage percentages
    def calc_percentage(current: int, limit: int | None) -> float:
        if not limit or limit == 0:
            return 0.0
        return (current / limit) * 100

    requests_pct = calc_percentage(current_requests, plan.max_requests_per_month)
    storage_pct = calc_percentage(int(current_storage_mb), plan.max_storage_mb)
    users_pct = calc_percentage(current_users, plan.max_users)
    functions_pct = calc_percentage(current_functions, plan.max_cloud_functions)

    # Check if unlimited
    is_unlimited_requests = (
        not plan.max_requests_per_month or plan.max_requests_per_month == 0
    )
    is_unlimited_storage = not plan.max_storage_mb or plan.max_storage_mb == 0
    is_unlimited_users = not plan.max_users or plan.max_users == 0
    is_unlimited_functions = (
        not plan.max_cloud_functions or plan.max_cloud_functions == 0
    )

    # Subscription details
    subscription_active = bool(subscription and subscription.is_active)
    subscription_ends = subscription.end_date if subscription else None
    days_remaining = subscription.days_remaining() if subscription else None
    auto_renew = subscription.auto_renew if subscription else False

    return PlanLimitsAnalytics(
        plan_name=plan.name if hasattr(plan, "name") else "Unknown",
        plan_price=plan.price if hasattr(plan, "price") else 0.0,
        plan_currency=plan.currency if hasattr(plan, "currency") else "USD",
        # Limits
        max_requests_per_month=plan.max_requests_per_month,
        max_storage_mb=plan.max_storage_mb,
        max_users=plan.max_users,
        max_cloud_functions=plan.max_cloud_functions,
        # Current Usage
        current_requests=current_requests,
        current_storage_mb=current_storage_mb,
        current_users=current_users,
        current_cloud_functions=current_functions,
        # Usage Percentages
        requests_usage_percentage=round(requests_pct, 2),
        storage_usage_percentage=round(storage_pct, 2),
        users_usage_percentage=round(users_pct, 2),
        functions_usage_percentage=round(functions_pct, 2),
        # Status
        is_unlimited_requests=is_unlimited_requests,
        is_unlimited_storage=is_unlimited_storage,
        is_unlimited_users=is_unlimited_users,
        is_unlimited_functions=is_unlimited_functions,
        # Subscription
        subscription_active=subscription_active,
        subscription_ends=subscription_ends,
        days_remaining=days_remaining,
        auto_renew=auto_renew,
    )


@router.get("/{project_id}/payments", response_model=PaymentAnalytics)
def get_payment_analytics(
    project_id: str,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Get comprehensive payment and revenue analytics.

    Includes:
    - Total payments by status
    - Revenue breakdown (total, monthly, yearly)
    - Average payment amount
    - Last payment details
    """
    current_month_start = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    current_year_start = datetime.now(timezone.utc).replace(
        month=1, day=1, hour=0, minute=0, second=0, microsecond=0
    )

    # OPTIMIZATION: Single aggregation query for all payment stats
    payment_stats = (
        db.query(
            func.count(Payment.id).label("total_payments"),
            func.count(case((Payment.status == "success", Payment.id))).label(
                "successful"
            ),
            func.count(case((Payment.status == "failed", Payment.id))).label("failed"),
            func.count(case((Payment.status == "pending", Payment.id))).label(
                "pending"
            ),
            func.sum(
                case((Payment.status == "success", Payment.amount), else_=0)
            ).label("total_revenue"),
            func.sum(
                case(
                    (
                        and_(
                            Payment.status == "success",
                            Payment.paid_at >= current_month_start,
                        ),
                        Payment.amount,
                    ),
                    else_=0,
                )
            ).label("revenue_month"),
            func.sum(
                case(
                    (
                        and_(
                            Payment.status == "success",
                            Payment.paid_at >= current_year_start,
                        ),
                        Payment.amount,
                    ),
                    else_=0,
                )
            ).label("revenue_year"),
            func.avg(case((Payment.status == "success", Payment.amount))).label(
                "avg_payment"
            ),
        )
        .filter(Payment.project_id == project_id)
        .first()
    )

    total_payments = payment_stats.total_payments or 0
    successful = payment_stats.successful or 0
    failed = payment_stats.failed or 0
    pending = payment_stats.pending or 0
    total_revenue = float(payment_stats.total_revenue or 0.0)
    revenue_month = float(payment_stats.revenue_month or 0.0)
    revenue_year = float(payment_stats.revenue_year or 0.0)
    avg_payment = float(payment_stats.avg_payment or 0.0)

    # Last payment details
    last_payment = (
        db.query(Payment)
        .filter(Payment.project_id == project_id, Payment.status == "success")
        .order_by(desc(Payment.paid_at))
        .first()
    )

    last_payment_date = last_payment.paid_at if last_payment else None
    last_payment_amount = last_payment.amount if last_payment else 0.0
    payment_method = last_payment.provider if last_payment else None

    return PaymentAnalytics(
        total_payments=total_payments,
        successful_payments=successful,
        failed_payments=failed,
        pending_payments=pending,
        total_revenue=total_revenue,
        revenue_this_month=revenue_month,
        revenue_this_year=revenue_year,
        average_payment=round(avg_payment, 2),
        last_payment_date=last_payment_date,
        last_payment_amount=last_payment_amount,
        payment_method=payment_method,
    )


@router.get("/{project_id}/payments/timeseries", response_model=List[TimeSeriesData])
def get_payments_timeseries(
    project_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """Get time-series data for successful payments (revenue over time)."""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    results = (
        db.query(
            func.date(Payment.paid_at).label("date"),
            func.sum(Payment.amount).label("revenue"),
        )
        .filter(
            Payment.project_id == project_id,
            Payment.status == "success",
            Payment.paid_at >= start_date,
            Payment.paid_at.isnot(None),
        )
        .group_by("date")
        .order_by("date")
        .all()
    )

    # Fill missing dates with 0
    date_map = {str(row.date): int(row.revenue or 0) for row in results}

    timeseries = []
    current_date = start_date.date()
    end_date = datetime.now(timezone.utc).date()

    while current_date <= end_date:
        date_str = str(current_date)
        timeseries.append(
            TimeSeriesData(date=date_str, value=date_map.get(date_str, 0))
        )
        current_date += timedelta(days=1)

    return timeseries


@router.get("/{project_id}/export")
async def export_analytics(
    project_id: str,
    format: str = Query("json", regex="^(json|csv)$"),
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Export comprehensive analytics data in JSON or CSV format.

    Includes:
    - Overview stats (with cloud functions, plan limits, payments)
    - Time-series data
    - Collection breakdown
    - Cloud function analytics
    - Plan limits and usage
    - Payment history
    """
    # Import other modules' functions
    from .overview import get_project_overview
    from .collections import get_collections_analytics, get_documents_timeseries
    from .users import get_user_analytics, get_users_timeseries, get_api_usage_analytics
    from .cloud_functions import get_cloud_functions_analytics

    # Gather all analytics
    overview = get_project_overview(project_id, db, project)
    collections = get_collections_analytics(project_id, db, project, limit=100)
    users = get_user_analytics(project_id, db, project)
    api_usage = get_api_usage_analytics(project_id, db, project)
    timeseries_docs = get_documents_timeseries(project_id, days, None, db, project)
    timeseries_users = get_users_timeseries(project_id, days, db, project)

    # New analytics
    cloud_functions = get_cloud_functions_analytics(project_id, db, project, limit=100)
    plan_limits = get_plan_limits_analytics(project_id, db, project)
    payments = get_payment_analytics(project_id, db, project)
    payments_timeseries = get_payments_timeseries(project_id, days, db, project)

    data = {
        "project_id": project_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "overview": overview.dict(),
        "collections": [c.dict() for c in collections],
        "users": users.dict(),
        "api_usage": api_usage.dict(),
        "cloud_functions": [cf.dict() for cf in cloud_functions],
        "plan_limits": plan_limits.dict(),
        "payments": payments.dict(),
        "timeseries": {
            "documents": [t.dict() for t in timeseries_docs],
            "users": [t.dict() for t in timeseries_users],
            "revenue": [t.dict() for t in payments_timeseries],
        },
    }

    if format == "json":
        json_str = json.dumps(data, indent=2, default=str)
        return StreamingResponse(
            io.BytesIO(json_str.encode()),
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="analytics_{project_id}.json"'
            },
        )
    else:
        # CSV format - flatten overview and key metrics
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["Comprehensive Analytics Export", f"Project: {project_id}"])
        writer.writerow(["Generated", datetime.now(timezone.utc).isoformat()])
        writer.writerow([])

        writer.writerow(["Overview Stats"])
        writer.writerow(["Metric", "Value"])
        for key, value in overview.dict().items():
            writer.writerow([key.replace("_", " ").title(), value])

        writer.writerow([])
        writer.writerow(["Collections"])
        if collections:
            writer.writerow(list(collections[0].dict().keys()))
            for col in collections:
                writer.writerow(list(col.dict().values()))

        writer.writerow([])
        writer.writerow(["Cloud Functions"])
        if cloud_functions:
            writer.writerow(list(cloud_functions[0].dict().keys()))
            for cf in cloud_functions:
                writer.writerow(list(cf.dict().values()))

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="analytics_{project_id}.csv"'
            },
        )
