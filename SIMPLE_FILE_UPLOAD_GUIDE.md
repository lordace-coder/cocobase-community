# Simple File Upload Guide - Named File Fields

## 🎯 The Simple Way

Upload files to specific fields by **just naming your file input**. No complex JSON mapping needed!

---

## Basic Usage

### cURL Example

```bash
# Upload avatar and wallpaper to specific fields
curl -X POST "http://localhost:8000/api/collections/documents?collection=users" \
  -H "x-api-key: your-api-key" \
  -F "data={\"name\":\"John Doe\",\"email\":\"john@example.com\"}" \
  -F "avatar=@avatar.jpg" \
  -F "wallpaper=@cover.jpg"
```

**Result:**

```json
{
  "id": "user-123",
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "avatar": "https://storage.example.com/.../avatar.jpg",
    "wallpaper": "https://storage.example.com/.../cover.jpg"
  }
}
```

---

## How It Works

1. **Name your file input** = the field name you want in the document
2. **That's it!** No JSON mapping, no indices, no complexity.

```bash
# Input name → Document field
-F "avatar=@file.jpg"      →  { "avatar": "url" }
-F "cover=@file.jpg"       →  { "cover": "url" }
-F "thumbnail=@file.jpg"   →  { "thumbnail": "url" }
```

---

## Examples

### User Profile (Avatar + Cover)

```bash
curl -X POST "http://localhost:8000/api/collections/documents?collection=users" \
  -H "x-api-key: your-key" \
  -F "data={\"name\":\"John\",\"role\":\"admin\"}" \
  -F "avatar=@profile-pic.jpg" \
  -F "cover_photo=@cover.jpg"
```

### Product (Main Image Only)

```bash
curl -X POST "http://localhost:8000/api/collections/documents?collection=products" \
  -H "x-api-key: your-key" \
  -F "data={\"name\":\"Laptop\",\"price\":1299}" \
  -F "main_image=@laptop.jpg"
```

### Blog Post (Featured Image + Multiple Inline Images)

```bash
curl -X POST "http://localhost:8000/api/collections/documents?collection=posts" \
  -H "x-api-key: your-key" \
  -F "data={\"title\":\"My Post\",\"content\":\"...\"}" \
  -F "featured_image=@hero.jpg" \
  -F "inline_images=@img1.jpg" \
  -F "inline_images=@img2.jpg" \
  -F "inline_images=@img3.jpg"
```

**Result:**

```json
{
  "title": "My Post",
  "featured_image": "https://.../hero.jpg",
  "inline_images": [
    "https://.../img1.jpg",
    "https://.../img2.jpg",
    "https://.../img3.jpg"
  ]
}
```

---

## Multiple Files → Array

**Upload multiple files with the same field name** to create an array:

```bash
curl -X POST "http://localhost:8000/api/collections/documents?collection=products" \
  -H "x-api-key: your-key" \
  -F "data={\"name\":\"Product\"}" \
  -F "gallery=@img1.jpg" \
  -F "gallery=@img2.jpg" \
  -F "gallery=@img3.jpg"
```

**Result:**

```json
{
  "name": "Product",
  "gallery": [
    "https://.../img1.jpg",
    "https://.../img2.jpg",
    "https://.../img3.jpg"
  ]
}
```

---

## JavaScript/Fetch

```javascript
const formData = new FormData();

// Document data
formData.append(
  "data",
  JSON.stringify({
    name: "John Doe",
    email: "john@example.com",
  })
);

// Named file fields - just use the field name!
formData.append("avatar", avatarFile);
formData.append("cover_photo", coverFile);

const response = await fetch(
  "http://localhost:8000/api/collections/documents?collection=users",
  {
    method: "POST",
    headers: { "x-api-key": "your-api-key" },
    body: formData,
  }
);

const result = await response.json();
console.log(result.data.avatar); // Avatar URL
console.log(result.data.cover_photo); // Cover photo URL
```

---

## React Component

```tsx
import React, { useState } from "react";

function UserProfileForm() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [coverFile, setCoverFile] = useState<File | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const formData = new FormData();
    formData.append("data", JSON.stringify({ name, email }));

    // Simple! Just name your fields
    if (avatarFile) formData.append("avatar", avatarFile);
    if (coverFile) formData.append("cover_photo", coverFile);

    const response = await fetch(
      "http://localhost:8000/api/collections/documents?collection=users",
      {
        method: "POST",
        headers: { "x-api-key": "your-api-key" },
        body: formData,
      }
    );

    const result = await response.json();
    console.log("User created:", result);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />

      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
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

## HTML Form

```html
<form
  method="POST"
  action="http://localhost:8000/api/collections/documents?collection=users"
  enctype="multipart/form-data"
>
  <input type="hidden" name="x-api-key" value="your-api-key" />

  <!-- Document data as JSON string -->
  <input
    type="hidden"
    name="data"
    value='{"name":"John Doe","email":"john@example.com"}'
  />

  <!-- Named file inputs - field name = form input name -->
  <label>
    Avatar:
    <input type="file" name="avatar" accept="image/*" />
  </label>

  <label>
    Cover Photo:
    <input type="file" name="cover_photo" accept="image/*" />
  </label>

  <button type="submit">Create User</button>
</form>
```

---

## Python Requests

```python
import requests
import json

url = "http://localhost:8000/api/collections/documents"
params = {"collection": "users"}
headers = {"x-api-key": "your-api-key"}

# Document data
data = {
    "data": (None, json.dumps({"name": "John Doe", "email": "john@example.com"}))
}

# Named file fields - tuple name = field name!
files = [
    ("avatar", ("avatar.jpg", open("avatar.jpg", "rb"), "image/jpeg")),
    ("cover_photo", ("cover.jpg", open("cover.jpg", "rb"), "image/jpeg"))
]

response = requests.post(url, params=params, headers=headers, data=data, files=files)
print(response.json())
```

---

## Update Document

### Update Avatar Only

```bash
curl -X PATCH "http://localhost:8000/api/collections/users/documents/user-123" \
  -H "x-api-key: your-key" \
  -F "avatar=@new-avatar.jpg"
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

### Update Multiple Fields

```bash
curl -X PATCH "http://localhost:8000/api/collections/users/documents/user-123" \
  -H "x-api-key: your-key" \
  -F "data={\"bio\":\"Updated bio\"}" \
  -F "avatar=@new-avatar.jpg" \
  -F "cover_photo=@new-cover.jpg"
```

---

## Default Behavior (Generic `files` Field)

If you want the old behavior (file_url/file_urls), just use `files` as the field name:

```bash
curl -X POST "http://localhost:8000/api/collections/documents?collection=products" \
  -H "x-api-key: your-key" \
  -F "data={\"name\":\"Product\"}" \
  -F "files=@image1.jpg" \
  -F "files=@image2.jpg"
```

**Result:**

```json
{
  "name": "Product",
  "file_urls": ["https://.../image1.jpg", "https://.../image2.jpg"]
}
```

---

## Comparison: Before vs After

### ❌ OLD WAY (Complex)

```bash
curl -X POST "..." \
  -F "files=@avatar.jpg" \
  -F "files=@cover.jpg" \
  -F "file_fields={\"avatar\":0,\"cover_photo\":1}"  # 😵 Complex!
```

### ✅ NEW WAY (Simple)

```bash
curl -X POST "..." \
  -F "avatar=@avatar.jpg" \
  -F "cover_photo=@cover.jpg"  # 😊 Easy!
```

---

## Key Points

### ✅ Benefits

1. **Super simple** - just name your input
2. **No JSON mapping** required
3. **Intuitive** - field name = input name
4. **Multiple files** → automatic array
5. **Backward compatible** - `files` field still works

### 📝 Rules

1. **Input name = Document field name**
   - `avatar=@file.jpg` → `{ "avatar": "url" }`
2. **Multiple files with same name = Array**
   - `gallery=@img1.jpg gallery=@img2.jpg` → `{ "gallery": ["url1", "url2"] }`
3. **Generic `files` field = Default behavior**
   - `files=@file.jpg` → `{ "file_url": "url" }`
   - `files=@file1.jpg files=@file2.jpg` → `{ "file_urls": ["url1", "url2"] }`

### ⚠️ Reserved Names

- `data` - Document JSON data
- `collection` - Collection name (query param)
- `id` - Collection ID (path param)
- `document_id` - Document ID (path param)

Don't use these as file field names!

---

## Common Patterns

### User Profiles

```bash
-F "avatar=@profile.jpg"
-F "cover_photo=@cover.jpg"
```

### E-commerce Products

```bash
-F "main_image=@main.jpg"
-F "gallery=@img1.jpg"
-F "gallery=@img2.jpg"
-F "gallery=@img3.jpg"
```

### Blog Posts

```bash
-F "featured_image=@hero.jpg"
-F "inline_images=@img1.jpg"
-F "inline_images=@img2.jpg"
```

### Real Estate Listings

```bash
-F "main_photo=@main.jpg"
-F "photos=@photo1.jpg"
-F "photos=@photo2.jpg"
-F "photos=@photo3.jpg"
-F "floor_plan=@plan.pdf"
```

---

## Summary

**It's now super simple!**

1. Name your file input with the field name you want
2. That's it!

```bash
# Want avatar field? Name it avatar!
-F "avatar=@file.jpg"

# Want gallery array? Use same name multiple times!
-F "gallery=@img1.jpg"
-F "gallery=@img2.jpg"
```

No complex JSON mapping, no indices, no confusion. Just **name your input = field name**! 🎉
