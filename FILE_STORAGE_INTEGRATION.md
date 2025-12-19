# CocoBase ORM - File Storage Integration

## 📦 Current Implementation (Python)

Your CocoBase system already has a complete file storage solution:

### **Storage Provider**
- **Service:** Backblaze B2 (S3-compatible)
- **Client:** aioboto3 (async S3 client for Python)
- **Bucket:** Configured via `BUCKET_NAME` env variable
- **Public URL:** `https://f005.backblazeb2.com/file/{bucket}/`

### **Storage Structure**
```
projects/
  {project_id}/
    media/              # Default directory
    avatars/            # User avatars
    documents/          # General documents
    {collection_name}/  # Collection-specific uploads
```

### **Key Features**
1. ✅ **Async uploads** - Non-blocking using aioboto3
2. ✅ **Storage tracking** - Cached in `projects.storage_used_bytes`
3. ✅ **Plan-based limits** - From `pricing_plans.max_storage_mb`
4. ✅ **Automatic notifications** - Alerts users when limit exceeded
5. ✅ **Document integration** - Files uploaded in multipart forms
6. ✅ **Collection scoping** - Files organized by collection

---

## 🔧 Python Functions (in app/storage/storage.py)

### 1. `handle_file_upload()`
```python
async def handle_file_upload(
    file_content: bytes,
    project_id: str,
    filename: str,
    subdirectory: str | None,
    db=None
) -> str:
    # Uploads to B2
    # Updates storage_used_bytes
    # Returns public URL
```

**What it does:**
- Creates S3 object key: `projects/{project_id}/{subdirectory}/{filename}`
- Uploads using aioboto3 (async)
- Increments `projects.storage_used_bytes`
- Returns: `https://f005.backblazeb2.com/file/{bucket}/projects/...`

---

### 2. `check_storage_limit()`
```python
def check_storage_limit(project_id: str, file_size: int, db):
    # Checks if upload would exceed plan limit
    # Sends notification if exceeded
    # Raises HTTPException(413)
```

**What it does:**
- Gets cached usage from `projects.storage_used_bytes`
- Gets plan limit from `pricing_plans.max_storage_mb`
- Compares: `current_usage + file_size > limit`
- If exceeded: sends notification + raises 413 error

---

### 3. `get_files()`
```python
def get_files(project_id: str, subdirectory: str | None):
    # Lists files in S3 bucket
    # Returns file metadata
```

**Returns:**
```python
[
    {
        "filename": "avatar.jpg",
        "url": "https://...",
        "size": 102400,
        "last_modified": "2025-01-18T...",
        "etag": "abc123..."
    }
]
```

---

### 4. `delete_s3_file()`
```python
def delete_s3_file(object_key: str) -> bool:
    # Deletes file from S3
    # TODO: Should decrement storage_used_bytes
```

**Note:** Currently missing storage cache update after deletion.

---

### 5. `update_project_storage_cache()`
```python
def update_project_storage_cache(
    project_id: str,
    file_size_delta: int,
    db
):
    # Updates projects.storage_used_bytes
    # Updates projects.storage_last_updated
```

---

## 🎯 ORM Integration Points

### **1. Standalone File Upload**
```http
POST /v1/storage/files
Authorization: Bearer coco_orm_...
Content-Type: multipart/form-data

file: [binary]
directory: "avatars"
```

**Implementation:**
- Call `check_storage_limit()` first
- Call `handle_file_upload()` for async upload
- Return file URL + metadata

---

### **2. Document Creation with Files**
```http
POST /v1/collections/users/documents
Content-Type: multipart/form-data

data: {"name": "John"}
avatar: [file]
resume: [file]
```

**Current Flow (Python):**
1. Parse multipart form data
2. Extract `data` field (JSON)
3. Loop through other fields
4. Check if field is `UploadFile`
5. Upload each file: `await handle_file_upload()`
6. Add file URLs to document data
7. Save document with URLs

**Your implementation (collections.py:164-279):**
- ✅ Handles multipart/form-data
- ✅ Uploads to `projects/{project_id}/{collection}/`
- ✅ Checks storage limits
- ✅ Adds URLs to document data

---

### **3. User Profile Updates**
```http
PATCH /v1/auth/me
Content-Type: multipart/form-data

data: {"name": "John"}
avatar: [file]
```

**Implementation:**
- Same pattern as document creation
- Upload to `projects/{project_id}/avatars/`
- Store URL in `app_users.data.avatar`

---

## 🚀 Go Implementation Guide

### **Required Go Package**
```go
import (
    "github.com/aws/aws-sdk-go-v2/aws"
    "github.com/aws/aws-sdk-go-v2/config"
    "github.com/aws/aws-sdk-go-v2/service/s3"
    "github.com/aws/aws-sdk-go-v2/credentials"
)
```

### **Configuration**
```go
type StorageConfig struct {
    B2KeyID       string
    B2AppKey      string
    B2Endpoint    string
    B2Bucket      string
    PublicBaseURL string
}

func NewS3Client(cfg StorageConfig) (*s3.Client, error) {
    r2Resolver := aws.EndpointResolverWithOptionsFunc(
        func(service, region string, options ...interface{}) (aws.Endpoint, error) {
            return aws.Endpoint{
                URL: cfg.B2Endpoint,
            }, nil
        },
    )

    awsCfg, err := config.LoadDefaultConfig(context.TODO(),
        config.WithEndpointResolverWithOptions(r2Resolver),
        config.WithCredentialsProvider(credentials.NewStaticCredentialsProvider(
            cfg.B2KeyID,
            cfg.B2AppKey,
            "",
        )),
    )

    return s3.NewFromConfig(awsCfg), nil
}
```

### **Upload Function**
```go
func (s *StorageService) UploadFile(
    ctx context.Context,
    projectID string,
    filename string,
    subdirectory string,
    content []byte,
) (string, error) {
    // 1. Check storage limit
    if err := s.checkStorageLimit(ctx, projectID, len(content)); err != nil {
        return "", err
    }

    // 2. Sanitize filename
    filename = strings.ReplaceAll(filename, " ", "_")

    // 3. Construct S3 key
    objectKey := fmt.Sprintf("projects/%s", projectID)
    if subdirectory != "" {
        objectKey += "/" + subdirectory
    }
    objectKey += "/" + filename

    // 4. Upload to S3
    _, err := s.s3Client.PutObject(ctx, &s3.PutObjectInput{
        Bucket: aws.String(s.bucket),
        Key:    aws.String(objectKey),
        Body:   bytes.NewReader(content),
    })
    if err != nil {
        return "", err
    }

    // 5. Update storage cache
    if err := s.updateStorageCache(ctx, projectID, len(content)); err != nil {
        log.Warn("Failed to update storage cache", "error", err)
    }

    // 6. Return public URL
    return s.publicBaseURL + objectKey, nil
}
```

### **Check Storage Limit**
```go
func (s *StorageService) checkStorageLimit(
    ctx context.Context,
    projectID string,
    fileSize int,
) error {
    // 1. Get cached usage
    project, err := s.db.GetProject(ctx, projectID)
    if err != nil {
        return err
    }

    currentUsage := project.StorageUsedBytes

    // 2. Get plan limit
    plan, err := s.db.GetCurrentPlan(ctx, projectID)
    if err != nil {
        return err
    }

    limitBytes := plan.MaxStorageMB * 1024 * 1024

    // 3. Check if would exceed
    if currentUsage + int64(fileSize) > limitBytes {
        // Send notification
        s.notifyStorageLimitExceeded(ctx, projectID, currentUsage, limitBytes)

        return &StorageLimitError{
            CurrentMB: float64(currentUsage) / 1024 / 1024,
            LimitMB:   float64(limitBytes) / 1024 / 1024,
        }
    }

    return nil
}
```

### **Update Storage Cache**
```go
func (s *StorageService) updateStorageCache(
    ctx context.Context,
    projectID string,
    sizeDelta int,
) error {
    return s.db.UpdateProjectStorage(ctx, projectID, sizeDelta)
}
```

---

## 📋 Database Fields Used

### **projects table**
```sql
storage_used_bytes   BIGINT    DEFAULT 0      -- Cached total size
storage_last_updated TIMESTAMP NULL           -- Last cache update
```

### **pricing_plans table**
```sql
max_storage_mb INTEGER NOT NULL  -- Storage limit per plan
```

---

## 🔐 Security Considerations

1. **File Sanitization**
   - Replace spaces with underscores
   - Validate file extensions (optional)
   - Check for path traversal attempts

2. **Storage Limits**
   - Always check before upload
   - Use atomic increment for storage cache
   - Handle race conditions (multiple uploads)

3. **Access Control**
   - Only project users can upload
   - Optional: user-specific directories
   - Optional: file permissions in database

4. **File Validation**
   - Max file size (e.g., 50 MB per file)
   - Allowed MIME types (optional)
   - Virus scanning (optional, future)

---

## 🎉 Benefits of Current System

1. ✅ **Async uploads** - No request blocking
2. ✅ **Cached storage** - Fast limit checks
3. ✅ **Public URLs** - Direct B2 access (no proxy)
4. ✅ **Project scoping** - Automatic organization
5. ✅ **Plan integration** - Automatic limits
6. ✅ **Collection integration** - Files in documents
7. ✅ **User notifications** - Automatic alerts

---

## 📝 TODO for Go Implementation

- [ ] Replicate `handle_file_upload()` in Go
- [ ] Replicate `check_storage_limit()` in Go
- [ ] Replicate `get_files()` in Go
- [ ] Fix `delete_s3_file()` to update storage cache
- [ ] Add file validation (MIME types, max size)
- [ ] Add concurrent upload handling
- [ ] Add retry logic for S3 failures
- [ ] Add file deletion tracking (audit log)
- [ ] Add storage usage recalculation endpoint (admin)

---

**Last Updated:** 2025-01-18
**Status:** Ready for Go Implementation
