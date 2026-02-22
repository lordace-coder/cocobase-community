"""
📦 Common Analytics Utilities
=============================

Shared utilities for all analytics modules:
- Caching layer (5-min TTL)
- Helper functions
- Response schemas (Pydantic models)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from functools import lru_cache


# ============================================
# CACHING LAYER
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
# HELPER FUNCTIONS
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
