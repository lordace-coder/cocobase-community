"""
☁️ Cloud Functions Analytics
============================

Cloud function execution analytics and logs.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, case, desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_dashboard_access
from app.models.app_client import Project
from app.models.cloud_functions import CloudFunction, FunctionExecution

from .common import (
    CloudFunctionAnalytics,
    FunctionExecutionLog,
    FunctionLogsAnalytics,
    TimeSeriesData,
)

router = APIRouter()


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
