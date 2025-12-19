# ORM API Keys - Rate Limit Implementation Changes

## Summary

Rate limits for ORM API keys are now **tied to pricing plans** instead of being set per individual key. This ensures consistent performance across all keys for a project and aligns with the subscription billing model.

## Changes Made

### 1. Database Schema Changes

#### Added to `pricing_plans` table:
```sql
ALTER TABLE pricing_plans
ADD COLUMN orm_rate_limit INTEGER;
```

This column stores the ORM API rate limit (requests per minute) for each pricing plan.

#### Removed from `orm_api_keys` table:
```sql
ALTER TABLE orm_api_keys
DROP COLUMN rate_limit;
```

Individual keys no longer have their own rate limits.

### 2. Rate Limits by Plan

| Plan ID | Plan Name   | Default Rate Limit (req/min) |
|---------|-------------|------------------------------|
| 1       | Free        | 100                          |
| 2       | Starter     | 500                          |
| 3       | Pro         | 2,000                        |
| 4       | Enterprise  | 5,000                        |

**Note:** These defaults are defined in the code but can be overridden by setting the `orm_rate_limit` column in the `pricing_plans` table.

### 3. Code Changes

#### File: `app/models/pricing.py`
- Added `orm_rate_limit` column to `PricingPlan` model

#### File: `app/models/orm_api_keys.py`
- Removed `rate_limit` field from `ORMApiKey` model

#### File: `app/schemas/orm_api_keys.py`
- Removed `rate_limit` from `ORMApiKeyCreate` schema
- Removed `rate_limit` from `ORMApiKeyResponse` schema
- Removed `rate_limit` from `ORMApiKeyCreateResponse` schema
- Removed `rate_limit` from `ORMApiKeyUpdate` schema

#### File: `app/api/orm_api_keys.py`
- Added `DEFAULT_RATE_LIMITS` dictionary mapping plan IDs to rate limits
- Removed `rate_limit` parameter from create/update operations
- Added new endpoint: `GET /project/{project_id}/orm-keys/rate-limit-info`

### 4. New API Endpoint

#### Get Rate Limit Info

```http
GET /project/{project_id}/orm-keys/rate-limit-info
Authorization: Bearer {your_auth_token}
```

**Response:**
```json
{
  "project_id": "proj-uuid",
  "plan_id": 3,
  "plan_name": "Pro",
  "orm_rate_limit": 2000,
  "requests_per_minute": 2000,
  "note": "This rate limit applies to all ORM API keys for this project"
}
```

This endpoint allows developers to query what rate limit applies to their project.

## Migration

### Migration Files Created:

1. **Initial ORM API Keys**: `d58bfa43b928_add_orm_api_keys_table.py`
2. **Rate Limit Changes**: `c3f10ca343f3_update_orm_keys_and_pricing_for_rate_.py`

Both migrations have been successfully applied.

### To Apply Migrations:
```bash
alembic upgrade head
```

### To Rollback:
```bash
alembic downgrade -1  # Rollback one migration
```

## Benefits

### 1. Simplified Billing
- Rate limits directly tied to subscription plans
- No confusion about different limits for different keys
- Easy to communicate pricing tiers to customers

### 2. Consistent Performance
- All keys for a project have the same rate limit
- Prevents inconsistent behavior across keys
- Easier to monitor and enforce

### 3. Easier Plan Management
- Change rate limits by updating the pricing plan
- Can override defaults for special cases using `orm_rate_limit` column
- Cleaner separation of concerns

### 4. Reduced Complexity
- Fewer fields to manage per API key
- Simpler API for creating keys
- Less opportunity for user error

## Implementation in ORM Microservice

When implementing the ORM microservice, rate limiting should work as follows:

1. **Key Validation**: When an ORM API key is received, validate it against the database
2. **Get Project**: Retrieve the project_id from the validated key
3. **Get Plan**: Query the project's active subscription to get the pricing plan
4. **Get Rate Limit**:
   - First check `pricing_plans.orm_rate_limit`
   - If NULL, use `DEFAULT_RATE_LIMITS[plan_id]`
5. **Apply Rate Limit**: Use Redis or in-memory counter to track requests per minute
6. **Reject if Exceeded**: Return 429 Too Many Requests if limit is exceeded

### Example Implementation Logic:

```python
# Pseudocode for ORM microservice
def get_rate_limit_for_key(orm_key: str, db: Session, redis: Redis) -> int:
    # 1. Validate and get key info
    key_record = validate_orm_key(orm_key, db)

    # 2. Get project's current plan
    plan = get_current_plan(key_record.project_id, db)

    # 3. Get rate limit
    rate_limit = plan.orm_rate_limit or DEFAULT_RATE_LIMITS.get(plan.id, 100)

    return rate_limit

def check_rate_limit(project_id: str, rate_limit: int, redis: Redis) -> bool:
    key = f"orm_rate_limit:{project_id}"
    current = redis.incr(key)

    if current == 1:
        redis.expire(key, 60)  # 60 seconds = 1 minute

    return current <= rate_limit
```

## Developer Experience

### Before (Per-Key Rate Limits):
```bash
POST /project/{id}/orm-keys
{
  "name": "My Key",
  "rate_limit": 1000  # User sets this
}
```

**Problems:**
- Users don't know what limit to set
- Could set unrealistic limits
- Different keys could have different limits
- Confusing for billing

### After (Plan-Based Rate Limits):
```bash
POST /project/{id}/orm-keys
{
  "name": "My Key"
  # No rate_limit field!
}

# To check limit:
GET /project/{id}/orm-keys/rate-limit-info
```

**Benefits:**
- Simpler API
- No confusion about limits
- Transparent pricing
- Consistent behavior

## Backward Compatibility

**Breaking Change:** If any existing code was setting `rate_limit` when creating ORM API keys, it will need to be updated to remove that field.

**Migration Impact:**
- Existing ORM API keys will have their `rate_limit` column removed
- Rate limits will now come from the pricing plan
- No data loss, just a structural change

## Testing Recommendations

1. **Create ORM API Key**: Verify `rate_limit` field is not accepted
2. **Get Rate Limit Info**: Verify endpoint returns correct plan-based limit
3. **Plan Upgrades**: Test that upgrading plan changes rate limit
4. **Custom Limits**: Test setting custom `orm_rate_limit` on pricing plan
5. **Default Fallback**: Test that NULL `orm_rate_limit` uses defaults

---

**Implementation Date:** 2025-12-19
**Status:** Complete
**Breaking Change:** Yes (rate_limit field removed from API)
