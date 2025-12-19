# ORM API Key Validation in Golang Backend

## Overview

The Golang ORM microservice needs to validate ORM API keys on every request to ensure security and proper authorization. Here's the complete validation flow.

## Validation Flow

```
Client Request → Extract Key → Validate Format → Database Lookup → Verify Hash → Check Status → Get Permissions → Allow/Deny
```

## Step-by-Step Implementation

### 1. Extract the API Key from Request Header

```go
// middleware/auth.go

import (
    "strings"
    "github.com/gofiber/fiber/v3"
)

func ExtractORMKey(c *fiber.Ctx) (string, error) {
    // Get Authorization header
    auth := c.Get("Authorization")

    if auth == "" {
        return "", fiber.NewError(401, "Missing Authorization header")
    }

    // Expected format: "Bearer coco_orm_project-123_abc...def"
    parts := strings.Split(auth, " ")
    if len(parts) != 2 || parts[0] != "Bearer" {
        return "", fiber.NewError(401, "Invalid Authorization header format")
    }

    return parts[1], nil
}
```

### 2. Validate Key Format

```go
// utils/validation.go

import (
    "strings"
    "regexp"
)

var ormKeyRegex = regexp.MustCompile(`^coco_orm_[a-f0-9-]{36}_[a-f0-9]{32}$`)

func ValidateORMKeyFormat(key string) (string, error) {
    // Check if key matches expected format
    if !ormKeyRegex.MatchString(key) {
        return "", errors.New("invalid ORM key format")
    }

    // Extract project_id from key
    // Format: coco_orm_<project_id>_<random>
    parts := strings.Split(key, "_")
    if len(parts) != 4 {
        return "", errors.New("malformed ORM key")
    }

    projectID := parts[2] // Extract project_id

    return projectID, nil
}
```

### 3. Database Lookup and Verification

```go
// models/orm_key.go

type ORMApiKey struct {
    ID         string    `db:"id"`
    ProjectID  string    `db:"project_id"`
    KeyHash    string    `db:"key_hash"`
    KeyPrefix  string    `db:"key_prefix"`
    Name       string    `db:"name"`
    Permissions map[string]interface{} `db:"permissions"`
    CreatedAt  time.Time `db:"created_at"`
    LastUsedAt *time.Time `db:"last_used_at"`
    ExpiresAt  *time.Time `db:"expires_at"`
    IsActive   bool      `db:"is_active"`
    CreatedBy  string    `db:"created_by"`
}

// repository/orm_key_repo.go

func (r *ORMKeyRepository) FindByPrefix(keyPrefix string) (*ORMApiKey, error) {
    var key ORMApiKey

    query := `
        SELECT id, project_id, key_hash, key_prefix, name, permissions,
               created_at, last_used_at, expires_at, is_active, created_by
        FROM orm_api_keys
        WHERE key_prefix = $1
    `

    err := r.db.Get(&key, query, keyPrefix)
    if err != nil {
        if err == sql.ErrNoRows {
            return nil, errors.New("API key not found")
        }
        return nil, err
    }

    return &key, nil
}
```

### 4. Verify Key Hash (bcrypt)

```go
// services/auth_service.go

import (
    "golang.org/x/crypto/bcrypt"
)

func (s *AuthService) VerifyORMKey(providedKey string) (*ORMApiKey, error) {
    // 1. Validate format and extract project_id
    projectID, err := ValidateORMKeyFormat(providedKey)
    if err != nil {
        return nil, err
    }

    // 2. Get key prefix (first 16 chars)
    keyPrefix := providedKey[:16]

    // 3. Lookup key in database by prefix
    keyRecord, err := s.ormKeyRepo.FindByPrefix(keyPrefix)
    if err != nil {
        return nil, err
    }

    // 4. Verify the hash matches
    err = bcrypt.CompareHashAndPassword(
        []byte(keyRecord.KeyHash),
        []byte(providedKey),
    )
    if err != nil {
        return nil, errors.New("invalid API key")
    }

    // 5. Check if key is active
    if !keyRecord.IsActive {
        return nil, errors.New("API key is deactivated")
    }

    // 6. Check if key is expired
    if keyRecord.ExpiresAt != nil && time.Now().After(*keyRecord.ExpiresAt) {
        return nil, errors.New("API key has expired")
    }

    // 7. Verify project_id matches
    if keyRecord.ProjectID != projectID {
        return nil, errors.New("project ID mismatch")
    }

    return keyRecord, nil
}
```

### 5. Get Rate Limit from Pricing Plan

```go
// services/rate_limit_service.go

type RateLimitInfo struct {
    ProjectID   string
    PlanID      int
    PlanName    string
    RateLimit   int
}

func (s *RateLimitService) GetRateLimit(projectID string) (*RateLimitInfo, error) {
    // Default rate limits per plan
    defaultLimits := map[int]int{
        1: 100,   // Free
        2: 500,   // Starter
        3: 2000,  // Pro
        4: 5000,  // Enterprise
    }

    // Query to get current plan for project
    query := `
        SELECT
            ps.project_id,
            pp.id as plan_id,
            pp.name as plan_name,
            pp.orm_rate_limit
        FROM project_subscriptions ps
        JOIN pricing_plans pp ON ps.plan_id = pp.id
        WHERE ps.project_id = $1
          AND ps.is_active = true
        ORDER BY ps.start_date DESC
        LIMIT 1
    `

    var result struct {
        ProjectID    string  `db:"project_id"`
        PlanID       int     `db:"plan_id"`
        PlanName     string  `db:"plan_name"`
        ORMRateLimit *int    `db:"orm_rate_limit"`
    }

    err := s.db.Get(&result, query, projectID)
    if err != nil {
        // Default to free plan if no subscription found
        return &RateLimitInfo{
            ProjectID: projectID,
            PlanID:    1,
            PlanName:  "Free",
            RateLimit: 100,
        }, nil
    }

    // Use custom rate limit if set, otherwise use default
    rateLimit := defaultLimits[result.PlanID]
    if result.ORMRateLimit != nil && *result.ORMRateLimit > 0 {
        rateLimit = *result.ORMRateLimit
    }

    return &RateLimitInfo{
        ProjectID: result.ProjectID,
        PlanID:    result.PlanID,
        PlanName:  result.PlanName,
        RateLimit: rateLimit,
    }, nil
}
```

### 6. Rate Limiting with Redis

```go
// middleware/rate_limiter.go

import (
    "github.com/redis/go-redis/v9"
    "context"
    "fmt"
)

func (m *RateLimiterMiddleware) CheckRateLimit(
    ctx context.Context,
    projectID string,
    limit int,
) error {
    // Redis key for rate limiting (per minute)
    key := fmt.Sprintf("orm_rate_limit:%s:%d", projectID, time.Now().Unix()/60)

    // Increment counter
    count, err := m.redis.Incr(ctx, key).Result()
    if err != nil {
        return err
    }

    // Set expiry on first request
    if count == 1 {
        m.redis.Expire(ctx, key, time.Minute)
    }

    // Check if limit exceeded
    if count > int64(limit) {
        return fiber.NewError(429, "Rate limit exceeded")
    }

    return nil
}
```

### 7. Update Last Used Timestamp

```go
// repository/orm_key_repo.go

func (r *ORMKeyRepository) UpdateLastUsed(keyID string) error {
    query := `
        UPDATE orm_api_keys
        SET last_used_at = NOW()
        WHERE id = $1
    `

    _, err := r.db.Exec(query, keyID)
    return err
}

// Note: Update this asynchronously to avoid blocking the request
func (r *ORMKeyRepository) UpdateLastUsedAsync(keyID string) {
    go func() {
        _ = r.UpdateLastUsed(keyID)
    }()
}
```

### 8. Complete Authentication Middleware

```go
// middleware/orm_auth.go

type ORMAuthMiddleware struct {
    authService      *AuthService
    rateLimitService *RateLimitService
    rateLimiter      *RateLimiterMiddleware
    ormKeyRepo       *ORMKeyRepository
}

func (m *ORMAuthMiddleware) Authenticate() fiber.Handler {
    return func(c *fiber.Ctx) error {
        // 1. Extract key from header
        apiKey, err := ExtractORMKey(c)
        if err != nil {
            return err
        }

        // 2. Verify key (format, database lookup, hash check, expiry, active status)
        keyRecord, err := m.authService.VerifyORMKey(apiKey)
        if err != nil {
            return fiber.NewError(401, "Invalid or expired API key")
        }

        // 3. Get rate limit for project
        rateLimitInfo, err := m.rateLimitService.GetRateLimit(keyRecord.ProjectID)
        if err != nil {
            return fiber.NewError(500, "Failed to get rate limit")
        }

        // 4. Check rate limit
        err = m.rateLimiter.CheckRateLimit(
            c.Context(),
            keyRecord.ProjectID,
            rateLimitInfo.RateLimit,
        )
        if err != nil {
            return err
        }

        // 5. Store key info in context for later use
        c.Locals("orm_key", keyRecord)
        c.Locals("project_id", keyRecord.ProjectID)
        c.Locals("permissions", keyRecord.Permissions)
        c.Locals("rate_limit", rateLimitInfo.RateLimit)

        // 6. Update last_used_at asynchronously
        m.ormKeyRepo.UpdateLastUsedAsync(keyRecord.ID)

        return c.Next()
    }
}
```

### 9. Usage in Routes

```go
// main.go or routes setup

func SetupRoutes(app *fiber.App, middleware *ORMAuthMiddleware) {
    // Apply ORM auth middleware to all /v1 routes
    v1 := app.Group("/v1", middleware.Authenticate())

    // All these routes are now protected and authenticated
    v1.Post("/collections/:collection/documents", handlers.CreateDocument)
    v1.Get("/collections/:collection/documents", handlers.GetDocuments)
    v1.Patch("/collections/:collection/documents/:id", handlers.UpdateDocument)
    v1.Delete("/collections/:collection/documents/:id", handlers.DeleteDocument)
}

// In handlers, access the authenticated info
func CreateDocument(c *fiber.Ctx) error {
    // Get project_id from context
    projectID := c.Locals("project_id").(string)

    // Get permissions
    permissions := c.Locals("permissions").(map[string]interface{})

    // Get ORM key info
    ormKey := c.Locals("orm_key").(*ORMApiKey)

    // Now create document scoped to this project
    // ...
}
```

## Permission Checking

```go
// middleware/permissions.go

func CheckPermission(
    permissions map[string]interface{},
    collection string,
    action string, // "read", "write", "delete"
) bool {
    collections, ok := permissions["collections"].(map[string]interface{})
    if !ok {
        return false
    }

    // Check wildcard permissions
    if wildcardPerms, ok := collections["*"].([]interface{}); ok {
        for _, perm := range wildcardPerms {
            if perm == action {
                return true
            }
        }
    }

    // Check collection-specific permissions
    if collectionPerms, ok := collections[collection].([]interface{}); ok {
        for _, perm := range collectionPerms {
            if perm == action {
                return true
            }
        }
    }

    return false
}

// Use in handlers
func CreateDocument(c *fiber.Ctx) error {
    collection := c.Params("collection")
    permissions := c.Locals("permissions").(map[string]interface{})

    if !CheckPermission(permissions, collection, "write") {
        return fiber.NewError(403, "Insufficient permissions")
    }

    // Proceed with create
    // ...
}
```

## Complete Example Request Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Client sends request with ORM API key                        │
│    POST /v1/collections/users/documents                         │
│    Authorization: Bearer coco_orm_proj-123_abc...def            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. Middleware extracts key from Authorization header            │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. Validate key format (regex check)                            │
│    Extract project_id from key                                  │
│    Get key_prefix (first 16 chars)                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. Database lookup by key_prefix                                │
│    SELECT * FROM orm_api_keys WHERE key_prefix = ?              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 5. Verify bcrypt hash                                           │
│    bcrypt.CompareHashAndPassword(stored_hash, provided_key)     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 6. Check key status                                             │
│    ✓ is_active = true                                           │
│    ✓ expires_at > now (or NULL)                                 │
│    ✓ project_id matches                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 7. Get rate limit from pricing plan                             │
│    SELECT pp.orm_rate_limit FROM project_subscriptions ps       │
│    JOIN pricing_plans pp ON ps.plan_id = pp.id                  │
│    WHERE ps.project_id = ? AND ps.is_active = true              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 8. Check rate limit (Redis)                                     │
│    INCR orm_rate_limit:proj-123:1234567890                      │
│    If count <= limit: Allow                                     │
│    If count > limit: Return 429 Too Many Requests               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 9. Check permissions                                            │
│    Does key have "write" permission for "users" collection?     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 10. Store context & proceed                                     │
│     c.Locals("project_id", "proj-123")                          │
│     c.Locals("permissions", {...})                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 11. Update last_used_at (async)                                 │
│     UPDATE orm_api_keys SET last_used_at = NOW()                │
│     WHERE id = ?                                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│ 12. Execute handler with project_id scope                       │
│     All queries automatically scoped to project_id              │
└─────────────────────────────────────────────────────────────────┘
```

## Security Best Practices

1. **Always use parameterized queries** - Prevent SQL injection
2. **Hash comparison in constant time** - bcrypt does this automatically
3. **Rate limit by project_id** - Not by IP to prevent bypassing
4. **Cache rate limits in Redis** - Fast lookups
5. **Update last_used_at asynchronously** - Don't block requests
6. **Log all authentication failures** - Security monitoring
7. **Validate project_id scoping** - Prevent cross-project access
8. **Use connection pooling** - Efficient database usage
9. **Implement request timeouts** - Prevent hanging requests
10. **Monitor rate limit hits** - Track abuse patterns

## Database Indexes Required

```sql
-- Already created in migration
CREATE INDEX idx_orm_keys_prefix ON orm_api_keys(key_prefix);
CREATE INDEX idx_orm_keys_project ON orm_api_keys(project_id);
CREATE INDEX idx_orm_keys_active ON orm_api_keys(is_active, project_id);

-- For optimal performance, ensure these exist
CREATE INDEX idx_project_subscriptions_project ON project_subscriptions(project_id, is_active);
CREATE INDEX idx_pricing_plans_active ON pricing_plans(id, is_active);
```

## Error Responses

```go
// 401 Unauthorized
{
  "success": false,
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or expired API key",
    "request_id": "req-uuid"
  }
}

// 429 Too Many Requests
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Limit: 2000 requests/minute",
    "retry_after": 45,
    "request_id": "req-uuid"
  }
}

// 403 Forbidden
{
  "success": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "Insufficient permissions for this operation",
    "required_permission": "write",
    "collection": "users",
    "request_id": "req-uuid"
  }
}
```

---

**Summary**: The Golang ORM backend validates keys through format checking, database lookup by prefix, bcrypt hash verification, status checks, rate limiting via Redis, and permission validation. All database queries are automatically scoped to the authenticated project_id.
