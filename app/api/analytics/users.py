"""
👥 Users Analytics
=================

User activity, signups, and engagement analytics.
"""

from datetime import datetime, timedelta, timezone
from typing import List
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_dashboard_access
from app.models.app_client import Project, AppUser

from .common import UserAnalytics, TimeSeriesData, ApiUsageAnalytics
from app.models.pricing import ApiUsageCounter, get_current_plan

router = APIRouter()


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
