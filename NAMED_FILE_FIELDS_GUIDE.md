# Named File Fields Guide

## Overview

Upload files to **specific fields** in your document data (like `avatar`, `wallpaper`, `cover_image`, etc.) instead of generic `file_url`/`file_urls` fields.

---

## Basic Concept

When uploading files with your documents, you can specify which field each file should be stored in:

```bash
# Upload avatar.jpg to "avatar" field and wallpaper.jpg to "wallpaper" field
POST /collections/documents?collection=users
Content-Type: multipart/form-data

data: {"name": "John Doe", "bio": "Developer"}
files: [avatar.jpg, wallpaper.jpg]
file_fields: {"avatar": 0, "wallpaper": 1}
```

**Result:**

```json
{
  "id": "user-123",
  "data": {
    "name": "John Doe",
    "bio": "Developer",
    "avatar": "https://storage.example.com/avatar.jpg",
    "wallpaper": "https://storage.example.com/wallpaper.jpg"
  }
}
```

---

## File Field Mapping

The `file_fields` parameter is a JSON object that maps field names to file indices:

```json
{
  "avatar": 0, // First file → avatar field
  "wallpaper": 1, // Second file → wallpaper field
  "cover": 2 // Third file → cover field
}
```

### File Indices

- Files are indexed starting from **0**
- Index corresponds to the position in the `files` array
- `files: [avatar.jpg, cover.jpg]` → avatar.jpg is index 0, cover.jpg is index 1

---

## Use Cases

### 1. Single File Per Field

Upload different files to different fields:

```bash
curl -X POST "http://localhost:8000/api/collections/documents?collection=users" \
  -H "x-api-key: your-api-key" \
  -F "data={\"name\":\"John\",\"email\":\"john@example.com\"}" \
  -F "files=@avatar.jpg" \
  -F "files=@wallpaper.jpg" \
  -F "file_fields={\"avatar\":0,\"wallpaper\":1}"
```

**Result:**

```json
{
  "name": "John",
  "email": "john@example.com",
  "avatar": "https://storage.example.com/projects/proj-123/users/avatar.jpg",
  "wallpaper": "https://storage.example.com/projects/proj-123/users/wallpaper.jpg"
}
```

---

### 2. Multiple Files in One Field (Array)

Store multiple files in a single array field (like a gallery):

```bash
curl -X POST "http://localhost:8000/api/collections/documents?collection=products" \
  -H "x-api-key: your-api-key" \
  -F "data={\"name\":\"Product 1\",\"price\":99.99}" \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg" \
  -F "files=@image3.jpg" \
  -F "file_fields={\"gallery\":[0,1,2]}"
```

**Result:**

```json
{
  "name": "Product 1",
  "price": 99.99,
  "gallery": [
    "https://storage.example.com/.../image1.jpg",
    "https://storage.example.com/.../image2.jpg",
    "https://storage.example.com/.../image3.jpg"
  ]
}
```

---

### 3. Mixed: Named + Unmapped Files

Some files mapped to specific fields, others use default behavior:

```bash
curl -X POST "http://localhost:8000/api/collections/documents?collection=posts" \
  -H "x-api-key: your-api-key" \
  -F "data={\"title\":\"My Post\"}" \
  -F "files=@cover.jpg" \
  -F "files=@attachment1.pdf" \
  -F "files=@attachment2.pdf" \
  -F "file_fields={\"cover_image\":0}"
```

**Result:**

```json
{
  "title": "My Post",
  "cover_image": "https://storage.example.com/.../cover.jpg",
  "file_urls": [
    "https://storage.example.com/.../attachment1.pdf",
    "https://storage.example.com/.../attachment2.pdf"
  ]
}
```

**Behavior:**

- File at index 0 → `cover_image` field (mapped)
- Files at indices 1, 2 → `file_urls` array (unmapped, default behavior)

---

### 4. User Profile Example

```bash
# Create user with avatar and cover photo
POST /collections/documents?collection=users
Content-Type: multipart/form-data

data: {
  "username": "johndoe",
  "email": "john@example.com",
  "role": "admin"
}
files: [avatar.jpg, cover.jpg]
file_fields: {"avatar": 0, "cover_photo": 1}
```

**Result:**

```json
{
  "id": "user-456",
  "username": "johndoe",
  "email": "john@example.com",
  "role": "admin",
  "avatar": "https://storage.example.com/projects/proj-123/users/avatar.jpg",
  "cover_photo": "https://storage.example.com/projects/proj-123/users/cover.jpg"
}
```

---

### 5. E-commerce Product Example

```bash
# Product with main image and gallery
POST /collections/documents?collection=products
Content-Type: multipart/form-data

data: {
  "name": "Laptop",
  "price": 1299.99,
  "category": "Electronics"
}
files: [main.jpg, gallery1.jpg, gallery2.jpg, gallery3.jpg]
file_fields: {
  "main_image": 0,
  "gallery": [1, 2, 3]
}
```

**Result:**

```json
{
  "name": "Laptop",
  "price": 1299.99,
  "category": "Electronics",
  "main_image": "https://storage.example.com/.../main.jpg",
  "gallery": [
    "https://storage.example.com/.../gallery1.jpg",
    "https://storage.example.com/.../gallery2.jpg",
    "https://storage.example.com/.../gallery3.jpg"
  ]
}
```

---

## Updating Documents

### Replace Specific Field

Update only the avatar, keep wallpaper unchanged:

```bash
PATCH /collections/users/documents/user-123
Content-Type: multipart/form-data

files: [new_avatar.jpg]
file_fields: {"avatar": 0}
```

**Before:**

```json
{
  "name": "John",
  "avatar": "https://old-avatar.jpg",
  "wallpaper": "https://old-wallpaper.jpg"
}
```

**After:**

```json
{
  "name": "John",
  "avatar": "https://new-avatar.jpg", // ✅ Updated
  "wallpaper": "https://old-wallpaper.jpg" // ✅ Preserved
}
```

---

### Update Multiple Fields

```bash
PATCH /collections/users/documents/user-123
Content-Type: multipart/form-data

data: {"bio": "Updated bio"}
files: [new_avatar.jpg, new_cover.jpg]
file_fields: {"avatar": 0, "cover_photo": 1}
```

Both `avatar` and `cover_photo` are replaced with new files.

---

## Default Behavior (No file_fields)

If you **don't** provide `file_fields`, files use the default behavior:

```bash
# Without file_fields
POST /collections/documents?collection=products
Content-Type: multipart/form-data

data: {"name": "Product"}
files: [image.jpg]
```

**Result:**

```json
{
  "name": "Product",
  "file_url": "https://storage.example.com/image.jpg" // Single file
}
```

```bash
# Multiple files without file_fields
files: [image1.jpg, image2.jpg]
```

**Result:**

```json
{
  "name": "Product",
  "file_urls": [
    // Multiple files
    "https://storage.example.com/image1.jpg",
    "https://storage.example.com/image2.jpg"
  ]
}
```

---

## JavaScript/TypeScript Examples

### Fetch API

```typescript
const formData = new FormData();

// Document data
formData.append(
  "data",
  JSON.stringify({
    name: "John Doe",
    email: "john@example.com",
    role: "user",
  })
);

// Files
const avatarFile = document.querySelector("#avatar-input").files[0];
const coverFile = document.querySelector("#cover-input").files[0];
formData.append("files", avatarFile);
formData.append("files", coverFile);

// Field mapping
formData.append(
  "file_fields",
  JSON.stringify({
    avatar: 0,
    cover_photo: 1,
  })
);

const response = await fetch(
  "http://localhost:8000/api/collections/documents?collection=users",
  {
    method: "POST",
    headers: {
      "x-api-key": "your-api-key",
    },
    body: formData,
  }
);

const result = await response.json();
console.log(result.data.avatar); // Avatar URL
console.log(result.data.cover_photo); // Cover photo URL
```

---

### Axios

```typescript
import axios from "axios";

const formData = new FormData();
formData.append("data", JSON.stringify({ name: "Product", price: 99.99 }));
formData.append("files", mainImageFile);
formData.append("files", gallery1File);
formData.append("files", gallery2File);
formData.append(
  "file_fields",
  JSON.stringify({
    main_image: 0,
    gallery: [1, 2],
  })
);

const response = await axios.post(
  "http://localhost:8000/api/collections/documents?collection=products",
  formData,
  {
    headers: {
      "x-api-key": "your-api-key",
      "Content-Type": "multipart/form-data",
    },
  }
);

console.log(response.data);
```

---

## React Component Example

```tsx
import React, { useState } from "react";

function UserProfileForm() {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    bio: "",
  });
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [coverFile, setCoverFile] = useState<File | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const data = new FormData();
    data.append("data", JSON.stringify(formData));

    if (avatarFile) data.append("files", avatarFile);
    if (coverFile) data.append("files", coverFile);

    // Map files to fields
    const fileMapping: any = {};
    let fileIndex = 0;
    if (avatarFile) {
      fileMapping.avatar = fileIndex++;
    }
    if (coverFile) {
      fileMapping.cover_photo = fileIndex++;
    }

    if (Object.keys(fileMapping).length > 0) {
      data.append("file_fields", JSON.stringify(fileMapping));
    }

    const response = await fetch(
      "http://localhost:8000/api/collections/documents?collection=users",
      {
        method: "POST",
        headers: { "x-api-key": "your-api-key" },
        body: data,
      }
    );

    const result = await response.json();
    console.log("Created user:", result);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Name"
        value={formData.name}
        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
      />

      <input
        type="email"
        placeholder="Email"
        value={formData.email}
        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
      />

      <textarea
        placeholder="Bio"
        value={formData.bio}
        onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
      />

      <label>
        Avatar:
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setAvatarFile(e.target.files?.[0] || null)}
        />
      </label>

      <label>
        Cover Photo:
        <input
          type="file"
          accept="image/*"
          onChange={(e) => setCoverFile(e.target.files?.[0] || null)}
        />
      </label>

      <button type="submit">Create User</button>
    </form>
  );
}
```

---

## Python Example

```python
import requests

# Create document with named file fields
url = "http://localhost:8000/api/collections/documents"
params = {"collection": "users"}
headers = {"x-api-key": "your-api-key"}

# Document data
data = {
    "name": "John Doe",
    "email": "john@example.com",
    "role": "admin"
}

# Files
files = [
    ("files", ("avatar.jpg", open("avatar.jpg", "rb"), "image/jpeg")),
    ("files", ("cover.jpg", open("cover.jpg", "rb"), "image/jpeg"))
]

# Form data
form_data = {
    "data": (None, json.dumps(data)),
    "file_fields": (None, json.dumps({"avatar": 0, "cover_photo": 1}))
}

response = requests.post(url, params=params, headers=headers, data=form_data, files=files)
print(response.json())
```

---

## Key Points

### ✅ Benefits

1. **Semantic field names**: `avatar` instead of `file_url`
2. **Multiple file fields**: Avatar, wallpaper, gallery, etc. in one document
3. **Selective updates**: Update only specific file fields
4. **Arrays supported**: Store multiple files in array fields
5. **Backward compatible**: Works with existing default behavior

### ⚠️ Important Notes

1. **File indices start at 0** (first file is 0, second is 1, etc.)
2. **Unmapped files** use default behavior (`file_url`/`file_urls`)
3. **Field mapping is optional** - omit for default behavior
4. **Arrays preserve order** - files mapped to array fields maintain their order
5. **Updates merge data** - existing fields not in payload are preserved

### 🔄 Update Behavior

- **With field mapping**: Only specified fields are updated
- **Without field mapping**: Uses default behavior (file_url/file_urls)
- **Unmapped files**: Appended to `file_urls` array

---

## Common Patterns

### User Profiles

```json
{
  "avatar": 0,
  "cover_photo": 1
}
```

### E-commerce Products

```json
{
  "main_image": 0,
  "gallery": [1, 2, 3, 4]
}
```

### Blog Posts

```json
{
  "featured_image": 0,
  "inline_images": [1, 2, 3]
}
```

### Documents/Articles

```json
{
  "thumbnail": 0,
  "attachments": [1, 2, 3]
}
```

### Real Estate Listings

```json
{
  "main_photo": 0,
  "photos": [1, 2, 3, 4, 5],
  "floor_plan": 6
}
```

---

## Error Handling

### Invalid file_fields JSON

```json
// ❌ Invalid JSON
file_fields: {avatar: 0}  // Missing quotes

// ✅ Valid JSON
file_fields: {"avatar": 0}
```

### Index Out of Range

```json
// If you only upload 2 files but reference index 3
files: [avatar.jpg, cover.jpg]
file_fields: {"photo": 3}  // ❌ File at index 3 doesn't exist

// Nothing will be stored in "photo" field
```

### Storage Limit Exceeded

```
HTTP 413 Payload Too Large
{
  "detail": "Storage limit exceeded. Current: 45.5MB, Limit: 50MB"
}
```

---

## Best Practices

1. **Use descriptive field names**: `avatar`, `cover_photo`, `gallery` instead of `img1`, `img2`
2. **Be consistent**: Use the same field names across your collection
3. **Validate on frontend**: Check file types and sizes before uploading
4. **Handle errors gracefully**: Show user-friendly error messages
5. **Optimize images**: Compress/resize before uploading to save storage
6. **Use appropriate file types**: JPEG/PNG for photos, WebP for web, etc.

---

## Summary

Named file fields give you **precise control** over where files are stored in your documents:

- **Map files to fields**: `{"avatar": 0, "wallpaper": 1}`
- **Arrays supported**: `{"gallery": [0, 1, 2]}`
- **Selective updates**: Update specific fields without affecting others
- **Backward compatible**: Works with existing file upload patterns
- **Flexible**: Mix named and unnamed files in the same request

Perfect for user profiles, product catalogs, blog posts, and any use case requiring multiple, semantically-named file fields! 🚀
