"""
📊 Overview Analytics
====================

Project overview and realtime metrics endpoints.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, and_, case, desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_dashboard_access
from app.models.app_client import Project, AppUser
from app.models.collections import Collection, Document
from app.models.pricing import (
    ApiUsageCounter,
    Payment,
    ProjectSubscription,
    get_current_plan,
)
from app.models.cloud_functions import CloudFunction, FunctionExecution
from app.storage.storage import get_project_usage

from .common import (
    OverviewStats,
    RealtimeMetrics,
    get_cached_data,
    set_cached_data,
    get_date_boundaries,
    calculate_percentage,
)

router = APIRouter()


@router.get("/{project_id}/overview", response_model=OverviewStats)
def get_project_overview(
    project_id: str,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
    force_refresh: bool = Query(False, description="Bypass cache"),
):
    """
    Get comprehensive project overview statistics.

    OPTIMIZED with caching (5-min TTL) and single-query aggregations.

    Returns:
    - Total collections, documents, users
    - API usage this month
    - Storage metrics
    - Today's activity
    - Cloud functions stats
    - Plan limits & usage
    - Payment information
    """
    # OPTIMIZATION: Check cache first
    cache_key = f"overview:{project_id}"
    if not force_refresh:
        cached = get_cached_data(cache_key)
        if cached:
            return OverviewStats(**cached)

    # Use helper for date boundaries
    today_start, now = get_date_boundaries(0)
    current_month = now.strftime("%Y-%m")

    # OPTIMIZATION: Single mega-query with subqueries for all counts
    counts_query = (
        db.query(
            func.count(func.distinct(Collection.id)).label("collections"),
            func.count(func.distinct(Document.id)).label("documents"),
            func.count(func.distinct(AppUser.id)).label("users"),
            func.count(
                func.distinct(case((Document.created_at >= today_start, Document.id)))
            ).label("docs_today"),
            func.count(
                func.distinct(case((AppUser.created_at >= today_start, AppUser.id)))
            ).label("users_today"),
            func.count(func.distinct(Document.collection_id)).label(
                "active_collections"
            ),
        )
        .select_from(Collection)
        .outerjoin(Document, Document.collection_id == Collection.id)
        .outerjoin(AppUser, AppUser.client_id == project_id)
        .filter(Collection.project_id == project_id)
        .first()
    )

    total_collections = counts_query.collections or 0
    total_documents = counts_query.documents or 0
    total_app_users = counts_query.users or 0
    documents_today = counts_query.docs_today or 0
    users_today = counts_query.users_today or 0
    active_collections = counts_query.active_collections or 0

    # API usage this month
    api_usage = (
        db.query(ApiUsageCounter.request_count)
        .filter(
            ApiUsageCounter.project_id == project_id,
            ApiUsageCounter.month == current_month,
        )
        .first()
    )
    total_api_calls = api_usage[0] if api_usage else 0

    # Cloud Functions stats (OPTIMIZED: single query)
    cf_stats = (
        db.query(
            func.count(func.distinct(CloudFunction.id)).label("total_functions"),
            func.count(func.distinct(FunctionExecution.id)).label("total_executions"),
            func.count(
                func.distinct(
                    case(
                        (
                            FunctionExecution.created_at >= today_start,
                            FunctionExecution.id,
                        )
                    )
                )
            ).label("executions_today"),
        )
        .select_from(CloudFunction)
        .outerjoin(FunctionExecution, FunctionExecution.function_id == CloudFunction.id)
        .filter(CloudFunction.project_id == project_id)
        .first()
    )

    total_cloud_functions = cf_stats.total_functions or 0
    total_function_executions = cf_stats.total_executions or 0
    cloud_functions_executed_today = cf_stats.executions_today or 0

    # Get current plan and limits
    plan = get_current_plan(project, db)

    # Get subscription details
    subscription = (
        db.query(ProjectSubscription)
        .filter(
            ProjectSubscription.project_id == project_id,
            ProjectSubscription.is_active == True,
        )
        .order_by(ProjectSubscription.start_date.desc())
        .first()
    )

    days_until_renewal = None
    active_subscription = bool(subscription)
    if subscription and subscription.end_date:
        days_until_renewal = subscription.days_remaining()

    # Calculate usage percentages (OPTIMIZED: use helper function)
    api_usage_pct = calculate_percentage(total_api_calls, plan.max_requests_per_month)

    storage_used_mb = round((get_project_usage(project_id) or 0) / 1024 / 1024, 2)
    storage_usage_pct = calculate_percentage(int(storage_used_mb), plan.max_storage_mb)

    users_usage_pct = calculate_percentage(total_app_users, plan.max_users)
    functions_usage_pct = calculate_percentage(
        total_cloud_functions, plan.max_cloud_functions
    )

    # Payment stats (OPTIMIZED: Single aggregation query)
    payment_stats = (
        db.query(
            func.count(Payment.id).label("total_payments"),
            func.sum(
                case((Payment.status == "success", Payment.amount), else_=0)
            ).label("total_revenue"),
        )
        .filter(Payment.project_id == project_id)
        .first()
    )

    total_payments = payment_stats.total_payments or 0
    total_revenue = float(payment_stats.total_revenue or 0.0)

    # Build response
    result_data = {
        "total_collections": total_collections,
        "total_documents": total_documents,
        "total_app_users": total_app_users,
        "total_api_calls_this_month": total_api_calls,
        "storage_used_mb": storage_used_mb,
        "active_collections": active_collections,
        "documents_created_today": documents_today,
        "users_created_today": users_today,
        # Cloud Functions
        "total_cloud_functions": total_cloud_functions,
        "cloud_functions_executed_today": cloud_functions_executed_today,
        "total_function_executions": total_function_executions,
        # Plan & Limits
        "current_plan": plan.name if hasattr(plan, "name") else "Unknown",
        "plan_price": plan.price if hasattr(plan, "price") else 0.0,
        "days_until_renewal": days_until_renewal,
        # Usage vs Limits
        "api_usage_percentage": api_usage_pct,
        "storage_usage_percentage": storage_usage_pct,
        "users_usage_percentage": users_usage_pct,
        "functions_usage_percentage": functions_usage_pct,
        # Financial
        "total_payments": total_payments,
        "total_revenue": total_revenue,
        "active_subscription": active_subscription,
    }

    # OPTIMIZATION: Cache the result for 5 minutes
    set_cached_data(cache_key, result_data)

    return OverviewStats(**result_data)


@router.get("/{project_id}/realtime", response_model=RealtimeMetrics)
def get_realtime_metrics(
    project_id: str,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Get real-time metrics for the dashboard.

    Returns metrics for:
    - Active users now
    - Requests in last hour
    - Documents created in last hour
    - Collections modified today
    - Function executions in last hour
    """
    now = datetime.now(timezone.utc)
    hour_ago = now - timedelta(hours=1)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # OPTIMIZATION: Single query for all metrics
    metrics = (
        db.query(
            # Active users (created in last 24h)
            func.count(
                func.distinct(
                    case((AppUser.created_at >= now - timedelta(hours=24), AppUser.id))
                )
            ).label("active_users"),
            # Documents in last hour
            func.count(
                func.distinct(case((Document.created_at >= hour_ago, Document.id)))
            ).label("docs_last_hour"),
            # Collections modified today
            func.count(
                func.distinct(case((Document.created_at >= today_start, Collection.id)))
            ).label("collections_modified"),
        )
        .select_from(Collection)
        .outerjoin(Document, Document.collection_id == Collection.id)
        .outerjoin(AppUser, AppUser.client_id == project_id)
        .filter(Collection.project_id == project_id)
        .first()
    )

    # API requests in last hour (estimate from current month counter)
    # This is an approximation since we don't track hourly granularity
    current_month = now.strftime("%Y-%m")
    monthly_requests = (
        db.query(ApiUsageCounter.request_count)
        .filter(
            ApiUsageCounter.project_id == project_id,
            ApiUsageCounter.month == current_month,
        )
        .first()
    )

    # Rough estimate: assume even distribution across days and hours
    day_of_month = now.day
    hour_of_day = now.hour
    total_hours = day_of_month * 24 + hour_of_day
    hourly_average = (
        int((monthly_requests[0] / total_hours) if total_hours > 0 else 0)
        if monthly_requests
        else 0
    )

    # Cloud function executions in last hour
    function_stats = (
        db.query(
            func.count(FunctionExecution.id).label("total"),
            func.count(
                case((FunctionExecution.status == "failed", FunctionExecution.id))
            ).label("failed"),
        )
        .filter(
            FunctionExecution.function_id.in_(
                db.query(CloudFunction.id).filter(
                    CloudFunction.project_id == project_id
                )
            ),
            FunctionExecution.created_at >= hour_ago,
        )
        .first()
    )

    functions_last_hour = function_stats.total or 0
    failed_functions_last_hour = function_stats.failed or 0

    return RealtimeMetrics(
        active_users_now=metrics.active_users or 0,
        requests_last_hour=hourly_average,
        documents_last_hour=metrics.docs_last_hour or 0,
        collections_modified_today=metrics.collections_modified or 0,
        functions_executed_last_hour=functions_last_hour,
        failed_executions_last_hour=failed_functions_last_hour,
    )
