# 📊 Analytics Module - Organized Structure

## Overview

The analytics module has been **split into logical, organized files** while maintaining all endpoints and functionality. This improves:

- ✅ **Code organization** - Related functionality grouped together
- ✅ **Maintainability** - Easier to find and update specific features
- ✅ **Performance** - No changes to optimization or caching
- ✅ **Import simplicity** - Single import point via `__init__.py`

---

## 📁 File Structure

```
app/api/analytics/
├── __init__.py              # Main router (combines all sub-routers)
├── common.py                # Shared utilities, cache, helpers, schemas
├── overview.py              # Project overview & realtime metrics
├── collections.py           # Collection analytics & timeseries
├── users.py                 # User analytics & API usage
├── cloud_functions.py       # Cloud function analytics & logs
└── plans_payments.py        # Plan limits, payments & export
```

---

## 📄 File Details

### 1. `__init__.py` - Main Router

**Purpose:** Combines all sub-routers into single analytics router

**Exports:**

- `router` - Combined APIRouter with all analytics endpoints

**Usage:**

```python
from app.api import analytics
app.include_router(analytics.router)  # All endpoints available
```

---

### 2. `common.py` - Shared Utilities

**Purpose:** Reusable code for all analytics modules

**Contains:**

- **Caching Layer:**

  - `get_cached_data(cache_key)` - Retrieve from cache
  - `set_cached_data(cache_key, data)` - Store in cache (5-min TTL)
  - `clear_project_cache(project_id)` - Clear project cache

- **Helper Functions:**

  - `get_date_boundaries(days_back)` - Cached date calculations
  - `calculate_percentage(current, maximum)` - Usage percentage helper

- **Response Schemas (Pydantic Models):**
  - `OverviewStats` - 27 fields (collections, users, functions, plan, payments)
  - `CollectionAnalytics` - 10 fields (documents, growth, activity)
  - `UserAnalytics` - 8 fields (totals, active users, retention)
  - `TimeSeriesData` - 2 fields (date, value)
  - `ApiUsageAnalytics` - 7 fields (requests, quota, usage %)
  - `TopCollections` - 3 fields (name, count, activity)
  - `RealtimeMetrics` - 6 fields (active users, requests, functions)
  - `CloudFunctionAnalytics` - 11 fields (executions, success rate, duration)
  - `FunctionExecutionLog` - 8 fields (execution details with logs)
  - `FunctionLogsAnalytics` - 7 fields (logs + error analysis)
  - `PlanLimitsAnalytics` - 21 fields (limits, usage, subscription)
  - `PaymentAnalytics` - 11 fields (payments, revenue breakdown)

---

### 3. `overview.py` - Overview & Realtime

**Purpose:** High-level project statistics and real-time metrics

**Endpoints:**
| Method | Path | Response Model | Description |
|--------|------|----------------|-------------|
| GET | `/{project_id}/overview` | `OverviewStats` | Complete project overview (cached 5 min) |
| GET | `/{project_id}/realtime` | `RealtimeMetrics` | Real-time dashboard metrics |

**Features:**

- ✅ In-memory caching with 5-min TTL
- ✅ `force_refresh` parameter to bypass cache
- ✅ Single mega-query optimization
- ✅ Includes cloud functions, plan limits, payments
- ✅ Real-time activity tracking (last hour)

**Dependencies:**

- `Project`, `AppUser`, `Collection`, `Document` models
- `CloudFunction`, `FunctionExecution` models
- `ApiUsageCounter`, `Payment`, `ProjectSubscription` models
- `get_project_usage()` from storage

---

### 4. `collections.py` - Collections Analytics

**Purpose:** Collection-specific analytics and document trends

**Endpoints:**
| Method | Path | Response Model | Description |
|--------|------|----------------|-------------|
| GET | `/{project_id}/collections` | `List[CollectionAnalytics]` | All collections analytics |
| GET | `/{project_id}/collections/{id}` | `CollectionAnalytics` | Single collection analytics |
| GET | `/{project_id}/timeseries/documents` | `List[TimeSeriesData]` | Document creation trends |
| GET | `/{project_id}/top-collections` | `List[TopCollections]` | Top collections by activity |

**Query Parameters:**

- `limit` - Max results (collections: 10, top: 10)
- `days` - Timeseries lookback (default: 30, max: 365)
- `collection_id` - Filter timeseries by collection
- `sort_by` - "total" or "recent" activity

**Features:**

- ✅ Growth rate calculations (week over week)
- ✅ Average documents per day
- ✅ Most active day detection
- ✅ Last updated timestamps
- ✅ Gap-filled timeseries (no missing dates)

**Dependencies:**

- `Collection`, `Document` models

---

### 5. `users.py` - Users & API Usage

**Purpose:** User activity, signups, and API request analytics

**Endpoints:**
| Method | Path | Response Model | Description |
|--------|------|----------------|-------------|
| GET | `/{project_id}/users` | `UserAnalytics` | Comprehensive user analytics |
| GET | `/{project_id}/timeseries/users` | `List[TimeSeriesData]` | User signup trends |
| GET | `/{project_id}/api-usage` | `ApiUsageAnalytics` | API usage & quota tracking |

**Query Parameters:**

- `days` - Timeseries lookback (default: 30, max: 365)

**Features:**

- ✅ Active users tracking (today/week/month)
- ✅ Retention rate calculations
- ✅ API quota monitoring
- ✅ Daily usage averages
- ✅ Remaining quota calculations

**Dependencies:**

- `AppUser` model
- `ApiUsageCounter` model
- `get_current_plan()` for limits

---

### 6. `cloud_functions.py` - Cloud Functions & Logs

**Purpose:** Cloud function execution analytics and log viewing

**Endpoints:**
| Method | Path | Response Model | Description |
|--------|------|----------------|-------------|
| GET | `/{project_id}/cloud-functions` | `List[CloudFunctionAnalytics]` | All functions analytics |
| GET | `/{project_id}/cloud-functions/{id}` | `CloudFunctionAnalytics` | Single function analytics |
| GET | `/{project_id}/cloud-functions/{id}/timeseries` | `List[TimeSeriesData]` | Execution trends |
| GET | `/{project_id}/cloud-functions/{id}/logs` | `FunctionLogsAnalytics` | Execution logs + analysis |
| GET | `/{project_id}/cloud-functions/{id}/logs/{exec_id}` | `FunctionExecutionLog` | Single execution details |
| GET | `/{project_id}/cloud-functions/logs/errors` | `List[FunctionExecutionLog]` | All failed executions |

**Query Parameters:**

- `limit` - Max results (functions: 50, logs: 50-500)
- `days` - Timeseries lookback (default: 30, max: 365)
- `status_filter` - "success", "failed", or "timeout"
- `hours` - Error lookback (default: 24, max: 168)

**Features:**

- ✅ Success rate calculations
- ✅ Average execution duration
- ✅ Most common trigger types
- ✅ Full execution logs with stack traces
- ✅ **Automatic error pattern detection**
- ✅ Common error analysis (top 10 errors)
- ✅ Error filtering and search
- ✅ Project-wide error monitoring

**Dependencies:**

- `CloudFunction`, `FunctionExecution` models

---

### 7. `plans_payments.py` - Plans, Payments & Export

**Purpose:** Subscription limits, payment analytics, and data export

**Endpoints:**
| Method | Path | Response Model | Description |
|--------|------|----------------|-------------|
| GET | `/{project_id}/plan-limits` | `PlanLimitsAnalytics` | Plan limits & usage |
| GET | `/{project_id}/payments` | `PaymentAnalytics` | Payment & revenue analytics |
| GET | `/{project_id}/payments/timeseries` | `List[TimeSeriesData]` | Revenue trends |
| GET | `/{project_id}/export` | JSON/CSV | Export all analytics |

**Query Parameters:**

- `days` - Timeseries lookback (default: 30, max: 365)
- `format` - "json" or "csv" for export

**Features:**

- ✅ **Complete plan limits breakdown**
  - Max requests, storage, users, functions
  - Current usage for each resource
  - Usage percentages
  - Unlimited plan detection
- ✅ **Revenue analytics**
  - Total/monthly/yearly revenue
  - Payment success/fail rates
  - Average payment amounts
  - Last payment details
- ✅ **Subscription status**
  - Active/inactive detection
  - Days until renewal
  - Auto-renew status
  - Expiration dates
- ✅ **Data export**
  - JSON format (structured)
  - CSV format (flattened)
  - Includes all analytics types

**Dependencies:**

- `Payment`, `ProjectSubscription`, `PricingPlan` models
- `get_current_plan()` helper
- `get_project_usage()` for storage
- **Cross-module imports** for export (all other modules)

---

## 🔄 Import Pattern

All modules import from `common.py`:

```python
from .common import (
    # Response Models
    OverviewStats,
    CollectionAnalytics,
    UserAnalytics,
    # ... other schemas

    # Cache functions
    get_cached_data,
    set_cached_data,
    clear_project_cache,

    # Helpers
    get_date_boundaries,
    calculate_percentage,
)
```

Each module exports its own `router`:

```python
router = APIRouter()

@router.get("/{project_id}/something")
def endpoint():
    pass
```

Main `__init__.py` combines all:

```python
from .overview import router as overview_router
from .collections import router as collections_router
# ... other routers

router = APIRouter(prefix="/analytics", tags=["Analytics"])
router.include_router(overview_router)
router.include_router(collections_router)
# ... include others
```

---

## 📊 Complete Endpoint List (19 total)

### Overview (2)

1. `GET /{project_id}/overview` - Project overview stats
2. `GET /{project_id}/realtime` - Real-time metrics

### Collections (4)

3. `GET /{project_id}/collections` - All collections
4. `GET /{project_id}/collections/{id}` - Single collection
5. `GET /{project_id}/timeseries/documents` - Document trends
6. `GET /{project_id}/top-collections` - Top by activity

### Users (3)

7. `GET /{project_id}/users` - User analytics
8. `GET /{project_id}/timeseries/users` - User signup trends
9. `GET /{project_id}/api-usage` - API usage tracking

### Cloud Functions (6)

10. `GET /{project_id}/cloud-functions` - All functions
11. `GET /{project_id}/cloud-functions/{id}` - Single function
12. `GET /{project_id}/cloud-functions/{id}/timeseries` - Execution trends
13. `GET /{project_id}/cloud-functions/{id}/logs` - Logs + analysis
14. `GET /{project_id}/cloud-functions/{id}/logs/{exec_id}` - Single log
15. `GET /{project_id}/cloud-functions/logs/errors` - All errors

### Plans & Payments (4)

16. `GET /{project_id}/plan-limits` - Limits & usage
17. `GET /{project_id}/payments` - Payment analytics
18. `GET /{project_id}/payments/timeseries` - Revenue trends
19. `GET /{project_id}/export` - Export all data

---

## ✅ Benefits of Modular Structure

### **1. Organization**

- Related endpoints grouped logically
- Easy to find specific functionality
- Clear separation of concerns

### **2. Maintainability**

- Update cloud functions without touching payments
- Add new collection endpoints in one place
- Shared code centralized in `common.py`

### **3. Performance**

- **No performance impact** - same optimizations
- Caching still works (5-min TTL)
- Single-query aggregations preserved

### **4. Developer Experience**

- Smaller files easier to navigate (200-400 lines each)
- Clear file names indicate content
- Single import point maintains simplicity

### **5. Testing**

- Can test modules independently
- Mock dependencies from `common.py`
- Isolated unit tests per module

---

## 🔧 Migration from Old Structure

### **Before:**

```python
# Single massive file
app/api/analytics.py (1929 lines)
```

### **After:**

```python
# Organized module
app/api/analytics/
├── __init__.py         (30 lines)   # Router combination
├── common.py           (280 lines)  # Shared code
├── overview.py         (260 lines)  # Overview + realtime
├── collections.py      (380 lines)  # Collections
├── users.py            (210 lines)  # Users + API usage
├── cloud_functions.py  (440 lines)  # Functions + logs
└── plans_payments.py   (420 lines)  # Plans + payments + export
```

### **No Code Changes Needed:**

```python
# This still works exactly the same!
from app.api import analytics
app.include_router(analytics.router)
```

---

## 🚀 Usage Examples

### Import the module (unchanged):

```python
from app.api import analytics
app.include_router(analytics.router)
```

### Call endpoints (unchanged):

```bash
# All endpoints work exactly as before
GET /analytics/{project_id}/overview
GET /analytics/{project_id}/cloud-functions/{id}/logs
GET /analytics/{project_id}/export?format=json
```

### Cache management (unchanged):

```python
from app.api.analytics.common import clear_project_cache
clear_project_cache("project-123")
```

---

## 📝 Summary

✅ **All 19 endpoints preserved**
✅ **All optimizations maintained** (caching, single queries)
✅ **All response models unchanged**
✅ **All query parameters the same**
✅ **No breaking changes** - drop-in replacement
✅ **Better organization** - 6 logical files vs 1 massive file
✅ **Easier maintenance** - find & update specific features faster
✅ **Same import** - `from app.api import analytics`

**Old file backed up:** `app/api/analytics_old_backup.py`

---

## 🎯 Next Steps

1. ✅ Test server starts successfully
2. ✅ Verify all endpoints respond
3. ✅ Check caching still works
4. ✅ Test cloud function logs
5. ✅ Validate export functionality
6. 📝 Update API documentation (if needed)
7. 🗑️ Delete backup file once confirmed working

**Everything should work exactly as before, just better organized!** 🎉
