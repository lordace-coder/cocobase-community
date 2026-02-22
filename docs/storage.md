# Storage API

Upload and manage files for your application.

**Base URL:** `https://api.cocobase.buzz/storage`

---

## Table of Contents

1. [Overview](#overview)
2. [Upload File](#upload-file)
3. [List Files](#list-files)
4. [Delete File](#delete-file)
5. [Storage Info](#storage-info)
6. [File Upload with User Signup/Update](#file-upload-with-user-signupupdate)
7. [Best Practices](#best-practices)

---

## Overview

CocoBase provides S3-compatible file storage for:
- User profile pictures
- Document attachments
- Media files
- Any file uploads

**Features:**
- Automatic S3 upload
- Storage limits per plan
- File organization by directories
- Direct URL access to files

---

## Upload File

Upload a file to your project storage.

**Endpoint:** `POST /storage/files/{project_id}`

**Headers:**
```bash
Content-Type: multipart/form-data
```

**Parameters:**
- `file` (required) - The file to upload
- `directory` (optional) - Subdirectory to organize files

### Basic Upload

```bash
curl -X POST https://api.cocobase.buzz/storage/files/your-project-id \
  -F "file=@/path/to/image.jpg"
```

**Response:**
```json
{
  "message": "File uploaded successfully",
  "s3_response": "https://your-bucket.s3.amazonaws.com/projects/your-project-id/image.jpg"
}
```

### Upload to Directory

```bash
curl -X POST https://api.cocobase.buzz/storage/files/your-project-id \
  -F "file=@/path/to/document.pdf" \
  -F "directory=documents"
```

**Response:**
```json
{
  "message": "File uploaded successfully",
  "s3_response": "https://your-bucket.s3.amazonaws.com/projects/your-project-id/documents/document.pdf"
}
```

### JavaScript Example

```javascript
async function uploadFile(projectId, file, directory = null) {
  const formData = new FormData();
  formData.append('file', file);

  if (directory) {
    formData.append('directory', directory);
  }

  const response = await fetch(
    `https://api.cocobase.buzz/storage/files/${projectId}`,
    {
      method: 'POST',
      body: formData
    }
  );

  return await response.json();
}

// Usage with file input
const fileInput = document.querySelector('input[type="file"]');
const file = fileInput.files[0];

const result = await uploadFile('your-project-id', file, 'avatars');
console.log('File URL:', result.s3_response);
```

### Python Example

```python
import requests

def upload_file(project_id, file_path, directory=None):
    url = f'https://api.cocobase.buzz/storage/files/{project_id}'

    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {}

        if directory:
            data['directory'] = directory

        response = requests.post(url, files=files, data=data)
        return response.json()

# Usage
result = upload_file('your-project-id', '/path/to/image.jpg', 'avatars')
print(f"File URL: {result['s3_response']}")
```

---

## List Files

Get all files in your project storage.

**Endpoint:** `GET /storage/files/{project_id}`

**Parameters:**
- `directory` (optional) - Filter by directory

### List All Files

```bash
curl https://api.cocobase.buzz/storage/files/your-project-id
```

**Response:**
```json
[
  {
    "key": "projects/your-project-id/image1.jpg",
    "size": 204800,
    "last_modified": "2024-01-15T10:30:00Z",
    "url": "https://your-bucket.s3.amazonaws.com/projects/your-project-id/image1.jpg"
  },
  {
    "key": "projects/your-project-id/documents/doc.pdf",
    "size": 512000,
    "last_modified": "2024-01-15T11:00:00Z",
    "url": "https://your-bucket.s3.amazonaws.com/projects/your-project-id/documents/doc.pdf"
  }
]
```

### List Files in Directory

```bash
curl "https://api.cocobase.buzz/storage/files/your-project-id?directory=documents"
```

**JavaScript:**
```javascript
async function listFiles(projectId, directory = null) {
  const params = new URLSearchParams();
  if (directory) {
    params.append('directory', directory);
  }

  const response = await fetch(
    `https://api.cocobase.buzz/storage/files/${projectId}?${params}`
  );

  return await response.json();
}

// Usage
const files = await listFiles('your-project-id', 'avatars');
console.log('Files:', files);
```

---

## Delete File

Delete a file from storage.

**Endpoint:** `DELETE /storage/files/{project_id}`

**Parameters:**
- `filename` (required) - The file name to delete
- `directory` (optional) - Directory where file is located

### Delete File

```bash
curl -X DELETE "https://api.cocobase.buzz/storage/files/your-project-id?filename=image.jpg"
```

**Response:**
```json
{}
```

### Delete File from Directory

```bash
curl -X DELETE "https://api.cocobase.buzz/storage/files/your-project-id?filename=document.pdf&directory=documents"
```

**JavaScript:**
```javascript
async function deleteFile(projectId, filename, directory = null) {
  const params = new URLSearchParams({ filename });
  if (directory) {
    params.append('directory', directory);
  }

  const response = await fetch(
    `https://api.cocobase.buzz/storage/files/${projectId}?${params}`,
    {
      method: 'DELETE'
    }
  );

  return await response.json();
}

// Usage
await deleteFile('your-project-id', 'old-avatar.jpg', 'avatars');
```

---

## Storage Info

Get storage usage information for your project.

**Endpoint:** `GET /storage/storage-info/{project_id}`

```bash
curl https://api.cocobase.buzz/storage/storage-info/your-project-id
```

**Response:**
```json
{
  "total_storage": 10737418240,
  "available": 9663676416,
  "used": 1073741824
}
```

**Fields:**
- `total_storage` - Total storage limit in bytes (based on plan)
- `used` - Storage currently used in bytes
- `available` - Remaining storage in bytes

**JavaScript:**
```javascript
async function getStorageInfo(projectId) {
  const response = await fetch(
    `https://api.cocobase.buzz/storage/storage-info/${projectId}`
  );

  const data = await response.json();

  return {
    totalGB: (data.total_storage / 1024 / 1024 / 1024).toFixed(2),
    usedGB: (data.used / 1024 / 1024 / 1024).toFixed(2),
    availableGB: (data.available / 1024 / 1024 / 1024).toFixed(2),
    usagePercent: ((data.used / data.total_storage) * 100).toFixed(1)
  };
}

// Usage
const storage = await getStorageInfo('your-project-id');
console.log(`Storage: ${storage.usedGB}GB / ${storage.totalGB}GB (${storage.usagePercent}%)`);
```

---

## File Upload with User Signup/Update

Files can be uploaded directly during user signup or profile updates.

### Signup with Profile Picture

```bash
curl -X POST https://api.cocobase.buzz/auth-collections/signup \
  -H "X-API-Key: your-api-key" \
  -F 'data={"email":"john@example.com","password":"password123","data":{"username":"johndoe"}}' \
  -F "profile_picture=@/path/to/image.jpg"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

The user's profile will include:
```json
{
  "id": "user_123",
  "email": "john@example.com",
  "data": {
    "username": "johndoe",
    "profile_picture": "https://your-bucket.s3.amazonaws.com/projects/project-id/users/image.jpg"
  }
}
```

### Update Profile with Multiple Files

```bash
curl -X PATCH https://api.cocobase.buzz/auth-collections/user \
  -H "Authorization: Bearer your-jwt-token" \
  -F 'data={"data":{"bio":"Updated bio"}}' \
  -F "profile_picture=@/path/to/new-avatar.jpg" \
  -F "cover_photo=@/path/to/cover.jpg"
```

**JavaScript:**
```javascript
async function updateProfileWithFiles(token, data, files) {
  const formData = new FormData();

  // Add JSON data
  formData.append('data', JSON.stringify({ data }));

  // Add files
  for (const [fieldName, file] of Object.entries(files)) {
    formData.append(fieldName, file);
  }

  const response = await fetch(
    'https://api.cocobase.buzz/auth-collections/user',
    {
      method: 'PATCH',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    }
  );

  return await response.json();
}

// Usage
const profilePicture = document.getElementById('avatar').files[0];
const coverPhoto = document.getElementById('cover').files[0];

const updatedUser = await updateProfileWithFiles(
  userToken,
  { bio: 'Software developer' },
  {
    profile_picture: profilePicture,
    cover_photo: coverPhoto
  }
);

console.log('Profile picture:', updatedUser.data.profile_picture);
console.log('Cover photo:', updatedUser.data.cover_photo);
```

---

## Best Practices

### 1. Validate Files Client-Side

```javascript
function validateImage(file) {
  // Check file type
  const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
  if (!allowedTypes.includes(file.type)) {
    alert('Only images are allowed (JPEG, PNG, GIF, WebP)');
    return false;
  }

  // Check file size (max 5MB)
  const maxSize = 5 * 1024 * 1024;
  if (file.size > maxSize) {
    alert('File too large. Max size is 5MB');
    return false;
  }

  return true;
}

// Usage
const fileInput = document.querySelector('input[type="file"]');
fileInput.addEventListener('change', (e) => {
  const file = e.target.files[0];
  if (validateImage(file)) {
    uploadFile(projectId, file);
  }
});
```

### 2. Show Upload Progress

```javascript
async function uploadFileWithProgress(projectId, file, onProgress) {
  const formData = new FormData();
  formData.append('file', file);

  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const percentComplete = (e.loaded / e.total) * 100;
        onProgress(percentComplete);
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status === 200) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        reject(new Error('Upload failed'));
      }
    });

    xhr.open('POST', `https://api.cocobase.buzz/storage/files/${projectId}`);
    xhr.send(formData);
  });
}

// Usage
const result = await uploadFileWithProgress(
  'your-project-id',
  file,
  (percent) => {
    console.log(`Upload progress: ${percent.toFixed(0)}%`);
    progressBar.style.width = `${percent}%`;
  }
);
```

### 3. Compress Images Before Upload

```javascript
async function compressImage(file, maxWidth = 1200, quality = 0.8) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let width = img.width;
        let height = img.height;

        if (width > maxWidth) {
          height = (height * maxWidth) / width;
          width = maxWidth;
        }

        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, width, height);

        canvas.toBlob((blob) => {
          resolve(new File([blob], file.name, {
            type: 'image/jpeg',
            lastModified: Date.now()
          }));
        }, 'image/jpeg', quality);
      };
      img.src = e.target.result;
    };
    reader.readAsDataURL(file);
  });
}

// Usage
const originalFile = fileInput.files[0];
const compressedFile = await compressImage(originalFile, 1200, 0.8);
await uploadFile('your-project-id', compressedFile);
```

### 4. Organize Files by Directory

```javascript
// Good organization structure
await uploadFile(projectId, profilePic, 'users/avatars');
await uploadFile(projectId, document, 'documents/invoices');
await uploadFile(projectId, postImage, 'posts/images');

// ❌ Bad: Everything in root
await uploadFile(projectId, file); // All files mixed together
```

### 5. Delete Old Files When Updating

```javascript
async function updateUserAvatar(token, projectId, newAvatar) {
  // Get current user
  const response = await fetch(
    'https://api.cocobase.buzz/auth-collections/user',
    {
      headers: { 'Authorization': `Bearer ${token}` }
    }
  );
  const user = await response.json();

  // Delete old avatar if exists
  if (user.data.profile_picture) {
    const oldFilename = user.data.profile_picture.split('/').pop();
    await deleteFile(projectId, oldFilename, 'users');
  }

  // Upload new avatar
  const formData = new FormData();
  formData.append('profile_picture', newAvatar);

  await fetch('https://api.cocobase.buzz/auth-collections/user', {
    method: 'PATCH',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
  });
}
```

### 6. Monitor Storage Usage

```javascript
async function checkStorageBeforeUpload(projectId, fileSize) {
  const storage = await getStorageInfo(projectId);

  if (fileSize > storage.available) {
    alert('Not enough storage space. Please upgrade your plan.');
    return false;
  }

  // Warn if close to limit
  const percentUsed = (storage.used / storage.total_storage) * 100;
  if (percentUsed > 90) {
    alert('Warning: Storage is almost full (${percentUsed.toFixed(0)}%)');
  }

  return true;
}

// Usage
const file = fileInput.files[0];
if (await checkStorageBeforeUpload('your-project-id', file.size)) {
  await uploadFile('your-project-id', file);
}
```

### 7. Handle Upload Errors

```javascript
async function safeUpload(projectId, file, directory) {
  try {
    const result = await uploadFile(projectId, file, directory);
    return { success: true, url: result.s3_response };
  } catch (error) {
    console.error('Upload failed:', error);

    // Check if it's a storage limit error
    if (error.message?.includes('storage limit')) {
      return {
        success: false,
        error: 'Storage limit reached. Please upgrade your plan.'
      };
    }

    return {
      success: false,
      error: 'Upload failed. Please try again.'
    };
  }
}

// Usage
const result = await safeUpload('your-project-id', file, 'avatars');
if (result.success) {
  console.log('File uploaded:', result.url);
} else {
  alert(result.error);
}
```

---

## Storage Limits by Plan

| Plan | Storage Limit |
|------|---------------|
| Free | 1 GB |
| Starter | 10 GB |
| Pro | 100 GB |
| Enterprise | Custom |

**Note:** Storage limits are enforced at upload time. You'll receive an error if you exceed your plan's limit.

---

## Supported File Types

CocoBase supports all file types, including:

- **Images:** JPEG, PNG, GIF, WebP, SVG
- **Documents:** PDF, DOC, DOCX, XLS, XLSX, PPT, PPTX
- **Media:** MP4, MP3, WAV, AVI
- **Archives:** ZIP, RAR, TAR, GZ
- **Code:** JS, HTML, CSS, JSON, XML

**Recommended max file sizes:**
- Images: 5 MB
- Documents: 10 MB
- Videos: 50 MB

---

## Next Steps

- **[Auth Collections](./auth-collections.md)** - Upload files during signup
- **[Collections API](./collections.md)** - Store file URLs in documents

---

**Need Help?** Contact support@cocobase.com
