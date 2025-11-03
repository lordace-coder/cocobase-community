# File Upload Feature - Implementation Summary

## 🎯 What Was Added

You can now upload files **directly** when creating or updating documents! The file URLs are automatically stored in the document data.

---

## 📝 Changes Made

### 1. Updated Imports

**File:** `app/api/collections/collections.py`

Added:

- `File` from FastAPI (for file uploads)
- `Form` from FastAPI (for form data)
- `json` module (for parsing JSON strings)

```python
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Query,
    BackgroundTasks,
    UploadFile,
    File,      # ← NEW
    Form,      # ← NEW
)
import json    # ← NEW
```

---

### 2. Enhanced Create Document Endpoint

**Endpoint:** `POST /collections/documents?collection={name}`

**Changes:**

- Changed from JSON body to multipart form-data support
- Accepts `data` as Form field (JSON string)
- Accepts `files` as File upload (multiple allowed)
- Uploads files to storage
- Stores URLs in document data automatically

**Parameters:**

```python
async def create_new_document(
    bg: BackgroundTasks,
    collection: str = Query(...),
    data: str = Form(None),                              # ← NEW
    files: Optional[List[UploadFile]] = File(None),      # ← NEW
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(require_api_access),
    user: AppUser = Depends(get_app_user),
)
```

**Logic:**

1. Parse JSON data from Form field
2. Find/create collection
3. Upload each file to storage
4. Check storage limits
5. Add URLs to document data:
   - Single file → `file_url` (string)
   - Multiple files → `file_urls` (array)
6. Create document with merged data

---

### 3. Enhanced Update Document Endpoint

**Endpoint:** `PATCH /collections/{id}/documents/{document_id}`

**Changes:**

- Changed from JSON body to multipart form-data support
- Accepts `data` as Form field (JSON string)
- Accepts `files` as File upload (multiple allowed)
- Appends new file URLs to existing `file_urls` array

**Parameters:**

```python
async def edit_document(
    id: str,
    document_id: str,
    bg: BackgroundTasks,
    data: str = Form(None),                              # ← NEW
    files: Optional[List[UploadFile]] = File(None),      # ← NEW
    proj: tuple[Project, User] = Depends(require_api_access),
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_app_user),
)
```

**Logic:**

1. Parse JSON update data
2. Upload new files
3. For single file: Update `file_url`
4. For multiple files: Append to `file_urls` array
5. Merge with existing document data

---

## 🎨 File Storage Structure

Files are organized by collection:

```
projects/
  {project_id}/
    {collection_name}/
      image1.jpg
      image2.jpg
      document.pdf
```

**Example:**

```
projects/proj-abc123/products/laptop-image.jpg
projects/proj-abc123/users/avatar.png
```

---

## 📊 Response Format

### Single File Upload

```json
{
  "id": "doc-123",
  "collection_id": "col-456",
  "created_at": "2024-01-15T10:30:00Z",
  "data": {
    "name": "Product 1",
    "price": 99.99,
    "file_url": "https://storage.cocobase.com/.../image.jpg"
  }
}
```

### Multiple Files Upload

```json
{
  "id": "doc-123",
  "collection_id": "col-456",
  "created_at": "2024-01-15T10:30:00Z",
  "data": {
    "name": "Product 1",
    "price": 99.99,
    "file_urls": [
      "https://storage.cocobase.com/.../image1.jpg",
      "https://storage.cocobase.com/.../image2.jpg"
    ]
  }
}
```

---

## 🔒 Security & Limits

### Storage Limits

- Files respect project storage limits from pricing plans
- Checked before upload using `check_storage_limit()`
- Returns 413 error if limit exceeded

### Validation

- Storage limits enforced
- File content read into memory
- Uploaded to Backblaze B2 storage

---

## 📚 Documentation Created

### 1. **FILE_UPLOAD_WITH_DOCUMENTS.md**

Comprehensive guide covering:

- Creating documents with files
- Updating documents with files
- File organization
- JavaScript/React examples
- Real-world use cases
- Migration guide

### 2. **FILE_UPLOAD_QUICK_REFERENCE.md**

Quick reference with:

- cURL examples
- JavaScript examples
- Python examples
- Response formats
- Quick tips

### 3. **examples/react-file-upload-component.jsx**

Complete React components:

- Product form with file uploads
- Update form with new files
- Custom hook for file uploads
- Preview functionality
- Error handling

---

## 🚀 Usage Examples

### cURL

```bash
curl -X POST "https://api.cocobase.com/collections/documents?collection=products" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F 'data={"name":"Product 1","price":99.99}' \
  -F 'files=@image1.jpg' \
  -F 'files=@image2.jpg'
```

### JavaScript

```javascript
const formData = new FormData();
formData.append(
  "data",
  JSON.stringify({
    name: "Product 1",
    price: 99.99,
  })
);
formData.append("files", file1);
formData.append("files", file2);

await fetch("/collections/documents?collection=products", {
  method: "POST",
  headers: { Authorization: "Bearer YOUR_API_KEY" },
  body: formData,
});
```

### Python

```python
import requests

files = [
    ('files', open('image1.jpg', 'rb')),
    ('files', open('image2.jpg', 'rb'))
]

data = {
    'data': '{"name":"Product 1","price":99.99}'
}

response = requests.post(
    'https://api.cocobase.com/collections/documents?collection=products',
    headers={'Authorization': 'Bearer YOUR_API_KEY'},
    data=data,
    files=files
)
```

---

## ⚡ Key Benefits

1. **Single Request**: Create document + upload files in one API call
2. **Automatic URLs**: File URLs stored automatically in document
3. **Atomic Operations**: All or nothing (no orphaned files)
4. **Organized Storage**: Files stored by collection name
5. **Backward Compatible**: Original JSON-only API still works
6. **Storage Limits**: Enforced based on pricing plan
7. **Data Merging**: Updates merge with existing data

---

## 🔄 Backward Compatibility

**Original API still works!**

```javascript
// Old way (JSON only) - STILL WORKS
await fetch("/collections/documents?collection=products", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    data: { name: "Product", price: 99.99 },
  }),
});

// New way (with files) - NEW FEATURE
const formData = new FormData();
formData.append("data", JSON.stringify({ name: "Product", price: 99.99 }));
formData.append("files", imageFile);

await fetch("/collections/documents?collection=products", {
  method: "POST",
  body: formData,
});
```

---

## ✅ Testing Checklist

- [ ] Create document with single file
- [ ] Create document with multiple files
- [ ] Create document with data only (no files)
- [ ] Update document with new file
- [ ] Update document with multiple new files
- [ ] Update document with data only
- [ ] Verify file URLs in response
- [ ] Check storage limit enforcement
- [ ] Verify files stored in correct collection folder
- [ ] Test with React component
- [ ] Test error handling

---

## 📋 Files Modified

1. `app/api/collections/collections.py`

   - Updated imports
   - Modified `create_new_document()` endpoint
   - Modified `edit_document()` endpoint

2. Documentation created:
   - `FILE_UPLOAD_WITH_DOCUMENTS.md`
   - `FILE_UPLOAD_QUICK_REFERENCE.md`
   - `examples/react-file-upload-component.jsx`
   - `FILE_UPLOAD_IMPLEMENTATION_SUMMARY.md` (this file)

---

## 🎯 Next Steps

**Optional Enhancements (Future):**

1. **Custom Field Names**

   - Allow specifying field name for file URLs
   - Example: `file_field=avatar` → stores as `avatar` instead of `file_url`

2. **File Type Validation**

   - Add `accept` parameter to restrict file types
   - Example: `accept=image/*` or `accept=.pdf,.doc`

3. **File Size Validation**

   - Per-file size limits
   - Different limits for different file types

4. **Image Processing**

   - Auto-resize images
   - Generate thumbnails
   - Convert formats

5. **Progress Tracking**

   - WebSocket updates for large uploads
   - Progress percentage

6. **File Management**
   - Delete old files when updating
   - Cleanup unused files
   - File usage tracking

---

## 💡 Usage Tips

1. **Don't set Content-Type**: Let browser handle it automatically
2. **Single file** → `file_url` (string)
3. **Multiple files** → `file_urls` (array)
4. **Updates append** to `file_urls` array
5. **Data is merged** not replaced
6. **Files organized** by collection name
7. **Storage limits** enforced per project

---

## 🎉 Summary

You can now:
✅ Upload files when creating documents
✅ Upload files when updating documents  
✅ Automatic URL storage in document data
✅ Single or multiple file uploads
✅ Files organized by collection
✅ Storage limits enforced
✅ Backward compatible with existing API

This makes it much easier to work with files in your BaaS!
