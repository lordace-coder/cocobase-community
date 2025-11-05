# ☁️ Cloud Function Logs Analytics - NEW ENDPOINTS

## Overview

**Cloud function execution logs are now fully implemented!** The analytics API now exposes comprehensive logging and error analysis for all cloud functions.

---

## 🆕 New Endpoints (4 total)

### 1. **Function Logs with Analytics**

Get recent execution logs with error analysis.

**Endpoint:** `GET /analytics/{project_id}/cloud-functions/{function_id}/logs`

**Query Parameters:**

- `limit` (int): Number of recent logs (1-500, default: 50)
- `status_filter` (string): Filter by status (`success`, `failed`, `timeout`)

**Response:**

```json
{
  "function_id": "func-uuid",
  "function_name": "process_payment",
  "total_executions": 1234,
  "error_count": 34,
  "average_duration_ms": 145.6,

  "recent_executions": [
    {
      "execution_id": "exec-uuid-1",
      "function_id": "func-uuid",
      "function_name": "process_payment",
      "status": "failed",
      "duration_ms": 234,
      "triggered_by": "http",
      "logs": "Error: Payment gateway timeout\n  at processPayment (line 45)\n  at handleRequest (line 12)",
      "created_at": "2025-11-05T10:30:00Z"
    }
  ],

  "common_errors": [
    {
      "error": "Error: Payment gateway timeout",
      "count": 12
    },
    {
      "error": "Error: Invalid API key",
      "count": 8
    }
  ]
}
```

**Use Cases:**

- View recent function executions
- Debug failures with full logs
- Identify common error patterns
- Monitor function reliability

---

### 2. **Single Execution Log**

Get detailed logs for one specific execution.

**Endpoint:** `GET /analytics/{project_id}/cloud-functions/{function_id}/logs/{execution_id}`

**Response:**

```json
{
  "execution_id": "exec-uuid",
  "function_id": "func-uuid",
  "function_name": "process_payment",
  "status": "failed",
  "duration_ms": 234,
  "triggered_by": "http",
  "logs": "Complete execution logs here...\nFull stack trace...",
  "created_at": "2025-11-05T10:30:00Z"
}
```

**Use Cases:**

- Deep dive into specific failure
- Get full stack trace
- Debugging individual executions

---

### 3. **All Function Errors (Project-Wide)**

Get all failed executions across ALL functions in the project.

**Endpoint:** `GET /analytics/{project_id}/cloud-functions/logs/errors`

**Query Parameters:**

- `hours` (int): Hours to look back (1-168, default: 24)
- `limit` (int): Max results (1-500, default: 100)

**Response:**

```json
[
  {
    "execution_id": "exec-1",
    "function_id": "func-1",
    "function_name": "process_payment",
    "status": "failed",
    "duration_ms": 234,
    "triggered_by": "http",
    "logs": "Error details...",
    "created_at": "2025-11-05T10:30:00Z"
  },
  {
    "execution_id": "exec-2",
    "function_id": "func-2",
    "function_name": "send_email",
    "status": "failed",
    "duration_ms": 123,
    "triggered_by": "schedule",
    "logs": "SMTP connection failed...",
    "created_at": "2025-11-05T09:15:00Z"
  }
]
```

**Use Cases:**

- Monitor all function failures
- Quick error overview
- Alert on high error rates
- SRE monitoring

---

### 4. **Existing Endpoints Enhanced**

The existing function analytics endpoint now returns better context for log analysis:

**Endpoint:** `GET /analytics/{project_id}/cloud-functions/{function_id}`

Returns execution counts that help understand log volume.

---

## 📊 Response Models

### FunctionExecutionLog

```python
{
  "execution_id": str,       # Unique execution ID
  "function_id": str,        # Function that was executed
  "function_name": str,      # Human-readable function name
  "status": str,             # success | failed | timeout
  "duration_ms": int,        # Execution time in milliseconds
  "triggered_by": str,       # manual | http | schedule | db-event
  "logs": str,               # Full execution logs (can be multi-line)
  "created_at": datetime     # When execution occurred
}
```

### FunctionLogsAnalytics

```python
{
  "function_id": str,
  "function_name": str,
  "total_executions": int,
  "recent_executions": List[FunctionExecutionLog],
  "error_count": int,
  "average_duration_ms": float,
  "common_errors": [
    {"error": str, "count": int}
  ]
}
```

---

## 🔥 Usage Examples

### JavaScript / TypeScript

```javascript
// Get recent logs for a function
const logs = await fetch(
  "/analytics/project-123/cloud-functions/func-456/logs?limit=100"
).then((r) => r.json());

console.log(`Total executions: ${logs.total_executions}`);
console.log(
  `Error rate: ${((logs.error_count / logs.total_executions) * 100).toFixed(
    2
  )}%`
);

// Display recent executions
logs.recent_executions.forEach((exec) => {
  if (exec.status === "failed") {
    console.error(`❌ ${exec.created_at}: ${exec.logs}`);
  }
});

// Show common errors
console.log("\nTop Errors:");
logs.common_errors.forEach((err, i) => {
  console.log(`${i + 1}. ${err.error} (${err.count} times)`);
});

// Get only failed executions
const failures = await fetch(
  "/analytics/project-123/cloud-functions/func-456/logs?status_filter=failed&limit=50"
).then((r) => r.json());

// Get specific execution details
const singleLog = await fetch(
  "/analytics/project-123/cloud-functions/func-456/logs/exec-789"
).then((r) => r.json());

console.log("Full execution log:", singleLog.logs);

// Monitor all errors across project
const allErrors = await fetch(
  "/analytics/project-123/cloud-functions/logs/errors?hours=24&limit=100"
).then((r) => r.json());

if (allErrors.length > 50) {
  alert(`⚠️ High error rate: ${allErrors.length} failures in last 24h`);
}
```

### Python

```python
import requests

base_url = 'http://localhost:8000/analytics/project-123'

# Get function logs with error analysis
logs = requests.get(
    f'{base_url}/cloud-functions/func-456/logs',
    params={'limit': 100}
).json()

print(f"Function: {logs['function_name']}")
print(f"Total Executions: {logs['total_executions']}")
print(f"Errors: {logs['error_count']}")
print(f"Error Rate: {logs['error_count'] / logs['total_executions'] * 100:.2f}%")

# Analyze error patterns
print("\nCommon Errors:")
for i, error in enumerate(logs['common_errors'], 1):
    print(f"{i}. {error['error']} ({error['count']} occurrences)")

# Get recent failures only
failures = requests.get(
    f'{base_url}/cloud-functions/func-456/logs',
    params={'status_filter': 'failed', 'limit': 50}
).json()

# Export failed logs to file
with open('function_errors.log', 'w') as f:
    for exec in failures['recent_executions']:
        f.write(f"\n{'='*80}\n")
        f.write(f"Execution ID: {exec['execution_id']}\n")
        f.write(f"Time: {exec['created_at']}\n")
        f.write(f"Duration: {exec['duration_ms']}ms\n")
        f.write(f"Logs:\n{exec['logs']}\n")

# Monitor all functions for errors
all_errors = requests.get(
    f'{base_url}/cloud-functions/logs/errors',
    params={'hours': 24, 'limit': 100}
).json()

# Group by function
from collections import defaultdict
errors_by_function = defaultdict(list)
for error in all_errors:
    errors_by_function[error['function_name']].append(error)

for func_name, errors in errors_by_function.items():
    print(f"{func_name}: {len(errors)} errors")
```

### cURL

```bash
# Get recent logs (last 50 executions)
curl http://localhost:8000/analytics/project-123/cloud-functions/func-456/logs

# Get only failures
curl "http://localhost:8000/analytics/project-123/cloud-functions/func-456/logs?status_filter=failed&limit=100"

# Get specific execution log
curl http://localhost:8000/analytics/project-123/cloud-functions/func-456/logs/exec-789

# Get all errors in last 24 hours
curl "http://localhost:8000/analytics/project-123/cloud-functions/logs/errors?hours=24&limit=100"

# Get errors from last week
curl "http://localhost:8000/analytics/project-123/cloud-functions/logs/errors?hours=168&limit=500"
```

---

## 🎯 Common Use Cases

### 1. **Error Monitoring Dashboard**

```javascript
async function buildErrorDashboard(projectId) {
  // Get all errors in last 24h
  const errors = await fetch(
    `/analytics/${projectId}/cloud-functions/logs/errors?hours=24`
  ).then((r) => r.json());

  // Calculate metrics
  const errorsByFunction = {};
  errors.forEach((err) => {
    errorsByFunction[err.function_name] =
      (errorsByFunction[err.function_name] || 0) + 1;
  });

  // Display
  console.log("Error Summary (Last 24h):");
  console.log(`Total Errors: ${errors.length}`);
  console.log("\nBy Function:");
  Object.entries(errorsByFunction)
    .sort((a, b) => b[1] - a[1])
    .forEach(([func, count]) => {
      console.log(`  ${func}: ${count} errors`);
    });
}
```

### 2. **Alert on High Error Rate**

```python
def check_function_health(project_id, function_id, threshold=5.0):
    """Alert if error rate exceeds threshold percentage"""
    logs = requests.get(
        f'/analytics/{project_id}/cloud-functions/{function_id}/logs',
        params={'limit': 100}
    ).json()

    error_rate = (logs['error_count'] / logs['total_executions']) * 100

    if error_rate > threshold:
        send_alert(
            f"⚠️ High error rate for {logs['function_name']}: "
            f"{error_rate:.2f}% ({logs['error_count']} errors)"
        )

        # Include top errors
        for error in logs['common_errors'][:3]:
            send_alert(f"  - {error['error']} ({error['count']} times)")
```

### 3. **Log Export & Analysis**

```python
def export_function_logs(project_id, function_id, output_file='logs.json'):
    """Export all recent logs for offline analysis"""
    logs = requests.get(
        f'/analytics/{project_id}/cloud-functions/{function_id}/logs',
        params={'limit': 500}
    ).json()

    # Save to file
    with open(output_file, 'w') as f:
        json.dump(logs, f, indent=2, default=str)

    print(f"Exported {len(logs['recent_executions'])} logs to {output_file}")
```

### 4. **Real-Time Error Monitoring**

```javascript
// Poll for new errors every 30 seconds
setInterval(async () => {
  const errors = await fetch(
    "/analytics/project-123/cloud-functions/logs/errors?hours=1&limit=10"
  ).then((r) => r.json());

  if (errors.length > 0) {
    showNotification(`⚠️ ${errors.length} new function errors`);

    // Update error badge
    document.getElementById("error-badge").textContent = errors.length;
  }
}, 30000);
```

---

## 🔍 Error Pattern Analysis

The `common_errors` field automatically analyzes error logs and groups similar errors:

```json
"common_errors": [
  {
    "error": "Error: Payment gateway timeout",
    "count": 12
  },
  {
    "error": "Error: Invalid API key",
    "count": 8
  },
  {
    "error": "TypeError: Cannot read property 'id' of undefined",
    "count": 5
  }
]
```

**How it works:**

- Extracts first line of error logs (first 100 chars)
- Groups identical error signatures
- Returns top 10 most common errors
- Sorted by frequency

**Use for:**

- Quick identification of recurring issues
- Prioritizing bug fixes
- Understanding failure patterns

---

## ⚡ Performance Optimizations

All endpoints are optimized:

- ✅ Single-query aggregations for stats
- ✅ Indexed queries on `created_at` and `function_id`
- ✅ Configurable limits to prevent large responses
- ✅ Efficient error pattern extraction

---

## 📚 Complete Endpoint Summary

| #   | Endpoint                               | Method | Description                   |
| --- | -------------------------------------- | ------ | ----------------------------- |
| 1   | `/cloud-functions/{id}/logs`           | GET    | Function logs with analytics  |
| 2   | `/cloud-functions/{id}/logs/{exec_id}` | GET    | Single execution details      |
| 3   | `/cloud-functions/logs/errors`         | GET    | All errors (project-wide)     |
| 4   | `/cloud-functions/{id}`                | GET    | Function analytics (existing) |
| 5   | `/cloud-functions/{id}/timeseries`     | GET    | Execution trends (existing)   |

**Total: 5 endpoints for comprehensive function monitoring!**

---

## ✅ Summary

**Yes, cloud function logs are now fully implemented!**

✅ **Recent execution logs** - View last N executions with full logs
✅ **Error analysis** - Automatic error pattern detection
✅ **Single execution details** - Deep dive into specific runs
✅ **Project-wide error monitoring** - See all failures across functions
✅ **Filtering** - By status (success/failed/timeout)
✅ **Configurable limits** - Control response size
✅ **Performance metrics** - Average duration, error counts
✅ **Production-ready** - Optimized queries, proper error handling

Perfect for building monitoring dashboards, alerting systems, and debugging tools! 🚀
