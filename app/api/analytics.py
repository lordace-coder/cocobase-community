"""
📊 Advanced Analytics API - OPTIMIZED
======================================

Comprehensive analytics endpoints for project insights, trends, and metrics.

Features:
- Project overview stats
- Collection analytics (growth, activity)
- User analytics (signups, active users)
- API usage tracking
- Time-series data
- Real-time metrics
- Export capabilities
- Cloud functions analytics
- Plan limits tracking
- Payment analytics

Performance Optimizations:
- In-memory caching (5-min TTL)
- Single-query aggregations
- Optimized JOINs
- Helper functions for date calculations
"""

from app.storage.storage import (
    check_storage_limit,
    delete_s3_file,
    get_files,
    handle_file_upload,
    get_project_usage,
)

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import func, and_, or_, cast, Integer, desc, case, extract
from sqlalchemy.orm import Session
from pydantic import BaseModel
from functools import lru_cache

from app.core.database import get_db
from app.core.dependencies import require_dashboard_access
from app.models.app_client import Project, AppUser
from app.models.collections import Collection, Document
from app.models.pricing import (
    ApiUsageCounter,
    Payment,
    PricingPlan,
    ProjectSubscription,
    get_current_plan,
)
from app.models.cloud_functions import CloudFunction, FunctionExecution
from app.models.user import User


router = APIRouter(prefix="/analytics", tags=["Analytics"])


# ============================================
# OPTIMIZATION: CACHING LAYER
# ============================================

# In-memory cache for frequently accessed data (5 min TTL)
_analytics_cache: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


def get_cached_data(cache_key: str) -> Optional[Dict[str, Any]]:
    """Get data from cache if not expired"""
    if cache_key in _analytics_cache:
        cached = _analytics_cache[cache_key]
        if (
            datetime.now(timezone.utc).timestamp() - cached["timestamp"]
            < CACHE_TTL_SECONDS
        ):
            return cached["data"]
        else:
            del _analytics_cache[cache_key]
    return None


def set_cached_data(cache_key: str, data: Any):
    """Store data in cache with timestamp"""
    _analytics_cache[cache_key] = {
        "data": data,
        "timestamp": datetime.now(timezone.utc).timestamp(),
    }


def clear_project_cache(project_id: str):
    """Clear all cache entries for a project"""
    keys_to_delete = [k for k in _analytics_cache.keys() if project_id in k]
    for key in keys_to_delete:
        del _analytics_cache[key]


# ============================================
# OPTIMIZATION: HELPER FUNCTIONS
# ============================================


@lru_cache(maxsize=128)
def get_date_boundaries(days_back: int = 0) -> tuple:
    """
    Cached helper to get common date boundaries.
    Cached for 1 hour to avoid repeated datetime calculations.
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    if days_back == 0:
        return (today_start, now)

    start_date = today_start - timedelta(days=days_back)
    return (start_date, now)


def calculate_percentage(current: int, maximum: Optional[int]) -> float:
    """Helper to calculate usage percentage"""
    if not maximum or maximum == 0:
        return 0.0
    return round((current / maximum) * 100, 2)


# ============================================
# RESPONSE SCHEMAS
# ============================================


class OverviewStats(BaseModel):
    """Project overview statistics"""

    total_collections: int
    total_documents: int
    total_app_users: int
    total_api_calls_this_month: int
    storage_used_mb: float
    active_collections: int
    documents_created_today: int
    users_created_today: int

    # Cloud Functions
    total_cloud_functions: int
    cloud_functions_executed_today: int
    total_function_executions: int

    # Plan & Limits
    current_plan: str
    plan_price: float
    days_until_renewal: Optional[int]

    # Usage vs Limits
    api_usage_percentage: float
    storage_usage_percentage: float
    users_usage_percentage: float
    functions_usage_percentage: float

    # Financial
    total_payments: int
    total_revenue: float
    active_subscription: bool


class CollectionAnalytics(BaseModel):
    """Analytics for a specific collection"""

    collection_id: str
    collection_name: str
    total_documents: int
    documents_today: int
    documents_this_week: int
    documents_this_month: int
    avg_documents_per_day: float
    growth_rate_percentage: float
    most_active_day: Optional[str]
    last_updated: Optional[datetime]


class UserAnalytics(BaseModel):
    """User activity analytics"""

    total_users: int
    active_users_today: int
    active_users_this_week: int
    active_users_this_month: int
    new_users_today: int
    new_users_this_week: int
    new_users_this_month: int
    retention_rate_percentage: float


class TimeSeriesData(BaseModel):
    """Time-series data point"""

    date: str
    value: int


class ApiUsageAnalytics(BaseModel):
    """API usage analytics"""

    total_requests_this_month: int
    requests_today: int
    daily_average: float
    peak_day: Optional[str]
    peak_requests: int
    remaining_quota: int
    usage_percentage: float


class TopCollections(BaseModel):
    """Top collections by activity"""

    collection_name: str
    document_count: int
    recent_activity: int


class RealtimeMetrics(BaseModel):
    """Real-time metrics"""

    active_users_now: int
    requests_last_hour: int
    documents_last_hour: int
    collections_modified_today: int
    functions_executed_last_hour: int
    failed_executions_last_hour: int


class CloudFunctionAnalytics(BaseModel):
    """Cloud function analytics"""

    function_id: str
    function_name: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate_percentage: float
    avg_duration_ms: float
    executions_today: int
    executions_this_week: int
    last_executed: Optional[datetime]
    most_common_trigger: Optional[str]


class FunctionExecutionLog(BaseModel):
    """Single function execution log entry"""

    execution_id: str
    function_id: str
    function_name: str
    status: str  # success, failed, timeout
    duration_ms: Optional[int]
    triggered_by: Optional[str]
    logs: Optional[str]  # Execution logs
    created_at: datetime


class FunctionLogsAnalytics(BaseModel):
    """Cloud function logs with analytics"""

    function_id: str
    function_name: str
    total_executions: int
    recent_executions: List[FunctionExecutionLog]
    error_count: int
    average_duration_ms: float
    common_errors: List[Dict[str, Any]]  # [{error: str, count: int}]


class PlanLimitsAnalytics(BaseModel):
    """Current plan limits and usage"""

    plan_name: str
    plan_price: float
    plan_currency: str

    # Limits
    max_requests_per_month: Optional[int]
    max_storage_mb: Optional[int]
    max_users: Optional[int]
    max_cloud_functions: Optional[int]

    # Current Usage
    current_requests: int
    current_storage_mb: float
    current_users: int
    current_cloud_functions: int

    # Usage Percentages
    requests_usage_percentage: float
    storage_usage_percentage: float
    users_usage_percentage: float
    functions_usage_percentage: float

    # Status
    is_unlimited_requests: bool
    is_unlimited_storage: bool
    is_unlimited_users: bool
    is_unlimited_functions: bool

    # Subscription
    subscription_active: bool
    subscription_ends: Optional[datetime]
    days_remaining: Optional[int]
    auto_renew: bool


class PaymentAnalytics(BaseModel):
    """Payment and revenue analytics"""

    total_payments: int
    successful_payments: int
    failed_payments: int
    pending_payments: int
    total_revenue: float
    revenue_this_month: float
    revenue_this_year: float
    average_payment: float
    last_payment_date: Optional[datetime]
    last_payment_amount: float
    payment_method: Optional[str]


# ============================================
# PROJECT OVERVIEW
# ============================================


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

    storage_used_mb = 0.0  # TODO: Calculate actual storage from get_project_usage()
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


# ============================================
# COLLECTION ANALYTICS
# ============================================


@router.get("/{project_id}/collections", response_model=List[CollectionAnalytics])
def get_collections_analytics(
    project_id: str,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
    limit: int = Query(10, ge=1, le=100),
):
    """
    Get analytics for all collections in the project.

    Includes:
    - Document counts
    - Growth metrics
    - Activity trends
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    collections = (
        db.query(Collection)
        .filter(Collection.project_id == project_id)
        .limit(limit)
        .all()
    )

    analytics_list = []

    for collection in collections:
        # Total documents
        total_docs = (
            db.query(func.count(Document.id))
            .filter(Document.collection_id == collection.id)
            .scalar()
            or 0
        )

        # Documents by time period
        docs_today = (
            db.query(func.count(Document.id))
            .filter(
                Document.collection_id == collection.id,
                Document.created_at >= today_start,
            )
            .scalar()
            or 0
        )

        docs_this_week = (
            db.query(func.count(Document.id))
            .filter(
                Document.collection_id == collection.id,
                Document.created_at >= week_start,
            )
            .scalar()
            or 0
        )

        docs_this_month = (
            db.query(func.count(Document.id))
            .filter(
                Document.collection_id == collection.id,
                Document.created_at >= month_start,
            )
            .scalar()
            or 0
        )

        # Average per day
        avg_per_day = docs_this_month / 30.0 if docs_this_month > 0 else 0.0

        # Growth rate (this week vs last week)
        last_week_start = week_start - timedelta(days=7)
        docs_last_week = (
            db.query(func.count(Document.id))
            .filter(
                Document.collection_id == collection.id,
                Document.created_at >= last_week_start,
                Document.created_at < week_start,
            )
            .scalar()
            or 0
        )

        growth_rate = 0.0
        if docs_last_week > 0:
            growth_rate = ((docs_this_week - docs_last_week) / docs_last_week) * 100
        elif docs_this_week > 0:
            growth_rate = 100.0

        # Most active day
        most_active = (
            db.query(
                func.date(Document.created_at).label("day"),
                func.count(Document.id).label("count"),
            )
            .filter(
                Document.collection_id == collection.id,
                Document.created_at >= month_start,
            )
            .group_by("day")
            .order_by(desc("count"))
            .first()
        )

        most_active_day = str(most_active[0]) if most_active else None

        # Last updated
        last_doc = (
            db.query(Document.created_at)
            .filter(Document.collection_id == collection.id)
            .order_by(desc(Document.created_at))
            .first()
        )

        last_updated = last_doc[0] if last_doc else None

        analytics_list.append(
            CollectionAnalytics(
                collection_id=collection.id,
                collection_name=collection.name,
                total_documents=total_docs,
                documents_today=docs_today,
                documents_this_week=docs_this_week,
                documents_this_month=docs_this_month,
                avg_documents_per_day=round(avg_per_day, 2),
                growth_rate_percentage=round(growth_rate, 2),
                most_active_day=most_active_day,
                last_updated=last_updated,
            )
        )

    return analytics_list


@router.get(
    "/{project_id}/collections/{collection_id}", response_model=CollectionAnalytics
)
def get_collection_analytics(
    project_id: str,
    collection_id: str,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """Get detailed analytics for a specific collection."""
    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.project_id == project_id)
        .first()
    )

    if not collection:
        raise HTTPException(404, "Collection not found")

    # Use the list endpoint logic for single collection
    analytics_list = get_collections_analytics(project_id, db, project, limit=1)
    return analytics_list[0] if analytics_list else None


# ============================================
# TIME-SERIES ANALYTICS
# ============================================


@router.get("/{project_id}/timeseries/documents", response_model=List[TimeSeriesData])
def get_documents_timeseries(
    project_id: str,
    days: int = Query(30, ge=1, le=365),
    collection_id: Optional[str] = None,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Get time-series data for document creation.

    Args:
    - days: Number of days to look back (default: 30)
    - collection_id: Filter by specific collection (optional)

    Returns daily document counts
    """
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        db.query(
            func.date(Document.created_at).label("date"),
            func.count(Document.id).label("count"),
        )
        .join(Collection)
        .filter(Collection.project_id == project_id, Document.created_at >= start_date)
    )

    if collection_id:
        query = query.filter(Document.collection_id == collection_id)

    results = query.group_by("date").order_by("date").all()

    # Fill missing dates with 0
    date_map = {str(row.date): row.count for row in results}

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


@router.get("/{project_id}/timeseries/users", response_model=List[TimeSeriesData])
def get_users_timeseries(
    project_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """Get time-series data for user signups."""
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    results = (
        db.query(
            func.date(AppUser.created_at).label("date"),
            func.count(AppUser.id).label("count"),
        )
        .filter(AppUser.client_id == project_id, AppUser.created_at >= start_date)
        .group_by("date")
        .order_by("date")
        .all()
    )

    # Fill missing dates
    date_map = {str(row.date): row.count for row in results}

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


# ============================================
# USER ANALYTICS
# ============================================


@router.get("/{project_id}/users", response_model=UserAnalytics)
def get_user_analytics(
    project_id: str,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Get comprehensive user analytics.

    Includes:
    - Total and active users
    - New user signups by period
    - Retention metrics
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    # Total users
    total_users = (
        db.query(func.count(AppUser.id))
        .filter(AppUser.client_id == project_id)
        .scalar()
        or 0
    )

    # New users by period
    new_today = (
        db.query(func.count(AppUser.id))
        .filter(AppUser.client_id == project_id, AppUser.created_at >= today_start)
        .scalar()
        or 0
    )

    new_this_week = (
        db.query(func.count(AppUser.id))
        .filter(AppUser.client_id == project_id, AppUser.created_at >= week_start)
        .scalar()
        or 0
    )

    new_this_month = (
        db.query(func.count(AppUser.id))
        .filter(AppUser.client_id == project_id, AppUser.created_at >= month_start)
        .scalar()
        or 0
    )

    # Active users (have any activity - simplified for now)
    # TODO: Track last_seen or last_activity timestamp
    active_today = new_today
    active_week = new_this_week
    active_month = new_this_month

    # Retention rate (users who signed up last month and are still active)
    last_month_start = month_start - timedelta(days=30)
    users_last_month = (
        db.query(func.count(AppUser.id))
        .filter(
            AppUser.client_id == project_id,
            AppUser.created_at >= last_month_start,
            AppUser.created_at < month_start,
        )
        .scalar()
        or 0
    )

    retention_rate = 0.0
    if users_last_month > 0:
        # Simplified: assume active users are retained
        retention_rate = (active_month / users_last_month) * 100

    return UserAnalytics(
        total_users=total_users,
        active_users_today=active_today,
        active_users_this_week=active_week,
        active_users_this_month=active_month,
        new_users_today=new_today,
        new_users_this_week=new_this_week,
        new_users_this_month=new_this_month,
        retention_rate_percentage=round(retention_rate, 2),
    )


# ============================================
# API USAGE ANALYTICS
# ============================================


@router.get("/{project_id}/api-usage", response_model=ApiUsageAnalytics)
def get_api_usage_analytics(
    project_id: str,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Get API usage analytics for the current month.

    Includes:
    - Total requests
    - Daily breakdown
    - Quota tracking
    """
    from app.models.pricing import get_current_plan

    current_month = datetime.now(timezone.utc).strftime("%Y-%m")

    # Current month usage
    usage_record = (
        db.query(ApiUsageCounter)
        .filter(
            ApiUsageCounter.project_id == project_id,
            ApiUsageCounter.month == current_month,
        )
        .first()
    )

    total_requests = usage_record.request_count if usage_record else 0

    # Get plan limits
    plan = get_current_plan(project, db)
    max_requests = plan.max_requests_per_month or 0
    remaining = max(0, max_requests - total_requests) if max_requests > 0 else 999999999
    usage_percentage = (
        (total_requests / max_requests * 100) if max_requests > 0 else 0.0
    )

    # Daily average (days in current month so far)
    days_in_month = datetime.now(timezone.utc).day
    daily_avg = total_requests / days_in_month if days_in_month > 0 else 0.0

    # TODO: Implement daily breakdown tracking for peak day
    # For now, use simplified metrics
    peak_day = None
    peak_requests = 0
    requests_today = 0  # Would need daily tracking

    return ApiUsageAnalytics(
        total_requests_this_month=total_requests,
        requests_today=requests_today,
        daily_average=round(daily_avg, 2),
        peak_day=peak_day,
        peak_requests=peak_requests,
        remaining_quota=remaining,
        usage_percentage=round(usage_percentage, 2),
    )


# ============================================
# TOP COLLECTIONS
# ============================================


@router.get("/{project_id}/top-collections", response_model=List[TopCollections])
def get_top_collections(
    project_id: str,
    limit: int = Query(10, ge=1, le=50),
    sort_by: str = Query("total", regex="^(total|recent)$"),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Get top collections by activity.

    Args:
    - limit: Number of collections to return
    - sort_by: "total" (total documents) or "recent" (recent activity)
    """
    if sort_by == "total":
        # Sort by total document count
        results = (
            db.query(
                Collection.name,
                func.count(Document.id).label("document_count"),
                func.count(
                    case(
                        (
                            Document.created_at
                            >= datetime.now(timezone.utc) - timedelta(days=7),
                            1,
                        )
                    )
                ).label("recent_activity"),
            )
            .outerjoin(Document)
            .filter(Collection.project_id == project_id)
            .group_by(Collection.id, Collection.name)
            .order_by(desc("document_count"))
            .limit(limit)
            .all()
        )
    else:
        # Sort by recent activity
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)
        results = (
            db.query(
                Collection.name,
                func.count(Document.id).label("document_count"),
                func.count(case((Document.created_at >= week_ago, 1))).label(
                    "recent_activity"
                ),
            )
            .outerjoin(Document)
            .filter(Collection.project_id == project_id)
            .group_by(Collection.id, Collection.name)
            .order_by(desc("recent_activity"))
            .limit(limit)
            .all()
        )

    return [
        TopCollections(
            collection_name=row.name,
            document_count=row.document_count,
            recent_activity=row.recent_activity,
        )
        for row in results
    ]


# ============================================
# REAL-TIME METRICS
# ============================================


@router.get("/{project_id}/realtime", response_model=RealtimeMetrics)
def get_realtime_metrics(
    project_id: str,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Get real-time metrics for live dashboards.

    Returns:
    - Active users (simplified)
    - Recent activity (last hour)
    - Collections modified today
    - Cloud function executions
    """
    hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # OPTIMIZATION: Single query with multiple counts
    realtime_stats = (
        db.query(
            func.count(
                func.distinct(case((Document.created_at >= hour_ago, Document.id)))
            ).label("docs_last_hour"),
            func.count(
                func.distinct(
                    case((Document.created_at >= today_start, Document.collection_id))
                )
            ).label("collections_today"),
            func.count(
                func.distinct(case((AppUser.created_at >= hour_ago, AppUser.id)))
            ).label("users_last_hour"),
        )
        .select_from(Collection)
        .outerjoin(Document, Document.collection_id == Collection.id)
        .outerjoin(AppUser, AppUser.client_id == project_id)
        .filter(Collection.project_id == project_id)
        .first()
    )

    docs_last_hour = realtime_stats.docs_last_hour or 0
    collections_today = realtime_stats.collections_today or 0
    active_users = realtime_stats.users_last_hour or 0

    # Cloud function executions last hour
    cf_stats = (
        db.query(
            func.count(FunctionExecution.id).label("total_executions"),
            func.count(
                case((FunctionExecution.status == "failed", FunctionExecution.id))
            ).label("failed_executions"),
        )
        .join(CloudFunction, CloudFunction.id == FunctionExecution.function_id)
        .filter(
            CloudFunction.project_id == project_id,
            FunctionExecution.created_at >= hour_ago,
        )
        .first()
    )

    functions_executed = cf_stats.total_executions or 0
    failed_executions = cf_stats.failed_executions or 0

    # TODO: Get actual API requests from Redis for last hour
    requests_last_hour = 0

    return RealtimeMetrics(
        active_users_now=active_users,
        requests_last_hour=requests_last_hour,
        documents_last_hour=docs_last_hour,
        collections_modified_today=collections_today,
        functions_executed_last_hour=functions_executed,
        failed_executions_last_hour=failed_executions,
    )


# ============================================
# CLOUD FUNCTIONS ANALYTICS
# ============================================


@router.get(
    "/{project_id}/cloud-functions", response_model=List[CloudFunctionAnalytics]
)
def get_cloud_functions_analytics(
    project_id: str,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
    limit: int = Query(50, ge=1, le=100),
):
    """
    Get detailed analytics for all cloud functions.

    Includes:
    - Execution counts (total, success, failed)
    - Success rates
    - Average execution duration
    - Activity trends
    - Common trigger types
    """
    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_start = today_start - timedelta(days=7)

    # Get all functions for this project
    functions = (
        db.query(CloudFunction)
        .filter(CloudFunction.project_id == project_id)
        .limit(limit)
        .all()
    )

    analytics_list = []

    for function in functions:
        # OPTIMIZATION: Single aggregation query per function
        stats = (
            db.query(
                func.count(FunctionExecution.id).label("total_executions"),
                func.count(
                    case((FunctionExecution.status == "success", FunctionExecution.id))
                ).label("successful"),
                func.count(
                    case((FunctionExecution.status == "failed", FunctionExecution.id))
                ).label("failed"),
                func.avg(FunctionExecution.duration_ms).label("avg_duration"),
                func.count(
                    case(
                        (
                            FunctionExecution.created_at >= today_start,
                            FunctionExecution.id,
                        )
                    )
                ).label("executions_today"),
                func.count(
                    case(
                        (
                            FunctionExecution.created_at >= week_start,
                            FunctionExecution.id,
                        )
                    )
                ).label("executions_week"),
                func.max(FunctionExecution.created_at).label("last_executed"),
            )
            .filter(FunctionExecution.function_id == function.id)
            .first()
        )

        total_exec = stats.total_executions or 0
        successful = stats.successful or 0
        failed = stats.failed or 0
        success_rate = (successful / total_exec * 100) if total_exec > 0 else 0.0
        avg_duration = float(stats.avg_duration or 0.0)

        # Most common trigger type
        common_trigger = (
            db.query(
                FunctionExecution.triggered_by,
                func.count(FunctionExecution.id).label("count"),
            )
            .filter(FunctionExecution.function_id == function.id)
            .group_by(FunctionExecution.triggered_by)
            .order_by(desc("count"))
            .first()
        )

        most_common_trigger = common_trigger[0] if common_trigger else None

        analytics_list.append(
            CloudFunctionAnalytics(
                function_id=function.id,
                function_name=function.name,
                total_executions=total_exec,
                successful_executions=successful,
                failed_executions=failed,
                success_rate_percentage=round(success_rate, 2),
                avg_duration_ms=round(avg_duration, 2),
                executions_today=stats.executions_today or 0,
                executions_this_week=stats.executions_week or 0,
                last_executed=stats.last_executed,
                most_common_trigger=most_common_trigger,
            )
        )

    return analytics_list


@router.get(
    "/{project_id}/cloud-functions/{function_id}", response_model=CloudFunctionAnalytics
)
def get_cloud_function_analytics(
    project_id: str,
    function_id: str,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """Get detailed analytics for a specific cloud function."""
    # Verify function belongs to project
    function = (
        db.query(CloudFunction)
        .filter(CloudFunction.id == function_id, CloudFunction.project_id == project_id)
        .first()
    )

    if not function:
        raise HTTPException(404, "Cloud function not found")

    # Use the list endpoint logic
    analytics_list = get_cloud_functions_analytics(project_id, db, project, limit=100)

    # Find the specific function
    for analytics in analytics_list:
        if analytics.function_id == function_id:
            return analytics

    raise HTTPException(404, "Analytics not found")


@router.get(
    "/{project_id}/cloud-functions/{function_id}/timeseries",
    response_model=List[TimeSeriesData],
)
def get_function_execution_timeseries(
    project_id: str,
    function_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """Get time-series data for function executions."""
    # Verify function belongs to project
    function = (
        db.query(CloudFunction)
        .filter(CloudFunction.id == function_id, CloudFunction.project_id == project_id)
        .first()
    )

    if not function:
        raise HTTPException(404, "Cloud function not found")

    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    results = (
        db.query(
            func.date(FunctionExecution.created_at).label("date"),
            func.count(FunctionExecution.id).label("count"),
        )
        .filter(
            FunctionExecution.function_id == function_id,
            FunctionExecution.created_at >= start_date,
        )
        .group_by("date")
        .order_by("date")
        .all()
    )

    # Fill missing dates with 0
    date_map = {str(row.date): row.count for row in results}

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


# ============================================
# CLOUD FUNCTION LOGS ANALYTICS (NEW)
# ============================================


@router.get(
    "/{project_id}/cloud-functions/{function_id}/logs",
    response_model=FunctionLogsAnalytics,
)
def get_function_logs(
    project_id: str,
    function_id: str,
    limit: int = Query(50, ge=1, le=500, description="Number of recent logs to fetch"),
    status_filter: Optional[str] = Query(None, regex="^(success|failed|timeout)$"),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Get cloud function execution logs with analytics.

    Returns:
    - Recent execution logs (with log content)
    - Error analysis
    - Performance metrics
    - Common failure patterns

    Query Parameters:
    - limit: Number of recent executions (default: 50, max: 500)
    - status_filter: Filter by status (success/failed/timeout)
    """
    # Verify function belongs to project
    function = (
        db.query(CloudFunction)
        .filter(CloudFunction.id == function_id, CloudFunction.project_id == project_id)
        .first()
    )

    if not function:
        raise HTTPException(404, "Cloud function not found")

    # OPTIMIZATION: Get analytics in single query
    stats = (
        db.query(
            func.count(FunctionExecution.id).label("total"),
            func.count(
                case((FunctionExecution.status == "failed", FunctionExecution.id))
            ).label("errors"),
            func.avg(FunctionExecution.duration_ms).label("avg_duration"),
        )
        .filter(FunctionExecution.function_id == function_id)
        .first()
    )

    total_executions = stats.total or 0
    error_count = stats.errors or 0
    avg_duration = float(stats.avg_duration or 0.0)

    # Get recent executions with logs
    query = db.query(FunctionExecution).filter(
        FunctionExecution.function_id == function_id
    )

    if status_filter:
        query = query.filter(FunctionExecution.status == status_filter)

    recent_executions_raw = (
        query.order_by(desc(FunctionExecution.created_at)).limit(limit).all()
    )

    # Map to response model
    recent_executions = [
        FunctionExecutionLog(
            execution_id=exec.id,
            function_id=exec.function_id,
            function_name=function.name,
            status=exec.status,
            duration_ms=exec.duration_ms,
            triggered_by=exec.triggered_by,
            logs=exec.logs,
            created_at=exec.created_at,
        )
        for exec in recent_executions_raw
    ]

    # Analyze common errors (extract error patterns from logs)
    error_executions = (
        db.query(FunctionExecution.logs)
        .filter(
            FunctionExecution.function_id == function_id,
            FunctionExecution.status == "failed",
            FunctionExecution.logs.isnot(None),
        )
        .limit(100)  # Analyze last 100 errors
        .all()
    )

    # Simple error pattern extraction
    error_patterns = {}
    for (log_text,) in error_executions:
        if not log_text:
            continue

        # Extract first line or first 100 chars as error signature
        error_sig = log_text.split("\n")[0][:100] if log_text else "Unknown error"
        error_patterns[error_sig] = error_patterns.get(error_sig, 0) + 1

    # Sort by frequency
    common_errors = [
        {"error": error, "count": count}
        for error, count in sorted(
            error_patterns.items(), key=lambda x: x[1], reverse=True
        )[
            :10
        ]  # Top 10 errors
    ]

    return FunctionLogsAnalytics(
        function_id=function.id,
        function_name=function.name,
        total_executions=total_executions,
        recent_executions=recent_executions,
        error_count=error_count,
        average_duration_ms=round(avg_duration, 2),
        common_errors=common_errors,
    )


@router.get(
    "/{project_id}/cloud-functions/{function_id}/logs/{execution_id}",
    response_model=FunctionExecutionLog,
)
def get_single_execution_log(
    project_id: str,
    function_id: str,
    execution_id: str,
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Get detailed logs for a specific function execution.

    Returns complete execution details including full logs.
    """
    # Verify function belongs to project
    function = (
        db.query(CloudFunction)
        .filter(CloudFunction.id == function_id, CloudFunction.project_id == project_id)
        .first()
    )

    if not function:
        raise HTTPException(404, "Cloud function not found")

    # Get specific execution
    execution = (
        db.query(FunctionExecution)
        .filter(
            FunctionExecution.id == execution_id,
            FunctionExecution.function_id == function_id,
        )
        .first()
    )

    if not execution:
        raise HTTPException(404, "Execution log not found")

    return FunctionExecutionLog(
        execution_id=execution.id,
        function_id=execution.function_id,
        function_name=function.name,
        status=execution.status,
        duration_ms=execution.duration_ms,
        triggered_by=execution.triggered_by,
        logs=execution.logs,
        created_at=execution.created_at,
    )


@router.get(
    "/{project_id}/cloud-functions/logs/errors",
    response_model=List[FunctionExecutionLog],
)
def get_all_function_errors(
    project_id: str,
    hours: int = Query(
        24, ge=1, le=168, description="Hours to look back (max: 1 week)"
    ),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    project: Project = Depends(require_dashboard_access),
):
    """
    Get all failed function executions across all functions in the project.

    Useful for monitoring and debugging.

    Query Parameters:
    - hours: Hours to look back (default: 24, max: 168 = 1 week)
    - limit: Max results to return (default: 100, max: 500)
    """
    time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Get all failed executions with function details
    failed_executions = (
        db.query(FunctionExecution, CloudFunction.name)
        .join(CloudFunction, CloudFunction.id == FunctionExecution.function_id)
        .filter(
            CloudFunction.project_id == project_id,
            FunctionExecution.status == "failed",
            FunctionExecution.created_at >= time_threshold,
        )
        .order_by(desc(FunctionExecution.created_at))
        .limit(limit)
        .all()
    )

    return [
        FunctionExecutionLog(
            execution_id=exec.id,
            function_id=exec.function_id,
            function_name=func_name,
            status=exec.status,
            duration_ms=exec.duration_ms,
            triggered_by=exec.triggered_by,
            logs=exec.logs,
            created_at=exec.created_at,
        )
        for exec, func_name in failed_executions
    ]


# ============================================
# PLAN LIMITS & USAGE ANALYTICS
# ============================================


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

    current_storage_mb = get_project_usage(project_id)

    # Calculate usage percentages
    def calc_percentage(current: int, limit: Optional[int]) -> float:
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


# ============================================
# PAYMENT ANALYTICS
# ============================================


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


# ============================================
# EXPORT ANALYTICS
# ============================================


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
    from fastapi.responses import StreamingResponse
    import json
    import io
    import csv

    # Gather all analytics
    overview = get_project_overview(project_id, db, project)
    collections = get_collections_analytics(project_id, db, project)
    users = get_user_analytics(project_id, db, project)
    api_usage = get_api_usage_analytics(project_id, db, project)
    timeseries_docs = get_documents_timeseries(project_id, days, None, db, project)
    timeseries_users = get_users_timeseries(project_id, days, db, project)

    # New analytics
    cloud_functions = get_cloud_functions_analytics(project_id, db, project)
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
        for key, value in overview.dict().items():
            writer.writerow([key.replace("_", " ").title(), value])

        writer.writerow([])
        writer.writerow(["Plan Limits & Usage"])
        for key, value in plan_limits.dict().items():
            writer.writerow([key.replace("_", " ").title(), value])

        writer.writerow([])
        writer.writerow(["User Analytics"])
        for key, value in users.dict().items():
            writer.writerow([key.replace("_", " ").title(), value])

        writer.writerow([])
        writer.writerow(["API Usage"])
        for key, value in api_usage.dict().items():
            writer.writerow([key.replace("_", " ").title(), value])

        writer.writerow([])
        writer.writerow(["Payment Analytics"])
        for key, value in payments.dict().items():
            writer.writerow([key.replace("_", " ").title(), value])

        writer.writerow([])
        writer.writerow(["Cloud Functions Summary"])
        writer.writerow(
            [
                "Function Name",
                "Total Executions",
                "Success Rate %",
                "Avg Duration (ms)",
                "Last Executed",
            ]
        )
        for cf in cloud_functions:
            writer.writerow(
                [
                    cf.function_name,
                    cf.total_executions,
                    cf.success_rate_percentage,
                    cf.avg_duration_ms,
                    cf.last_executed,
                ]
            )

        writer.writerow([])
        writer.writerow(["Collections Summary"])
        writer.writerow(["Collection", "Total Docs", "Growth Rate %", "Docs Today"])
        for coll in collections:
            writer.writerow(
                [
                    coll.collection_name,
                    coll.total_documents,
                    coll.growth_rate_percentage,
                    coll.documents_today,
                ]
            )

        return StreamingResponse(
            io.BytesIO(output.getvalue().encode()),
            media_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="analytics_{project_id}.csv"'
            },
        )
