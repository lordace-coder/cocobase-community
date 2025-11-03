# File Upload Feature - Summary

## ✨ What's New

Upload files **directly to specific fields** with a super simple API!

**Works for:**

1. ✅ Collection documents (products, posts, etc.)
2. ✅ App user profiles (avatars, cover photos, etc.)

---

## The Simple Way

Just **name your file input** = field name. No complex JSON mapping!

### Before (Complex):

```bash
-F "files=@avatar.jpg" \
-F "files=@cover.jpg" \
-F "file_fields={\"avatar\":0,\"cover_photo\":1}"  # 😵
```

### Now (Simple):

```bash
-F "avatar=@avatar.jpg" \
-F "cover_photo=@cover.jpg"  # 😊
```

---

## Quick Examples

### 1. Collection Documents

```bash
# User profile document
curl -X POST "http://localhost:8000/api/collections/documents?collection=users" \
  -H "x-api-key: your-key" \
  -F "data={\"name\":\"John\",\"email\":\"john@example.com\"}" \
  -F "avatar=@profile.jpg" \
  -F "cover_photo=@cover.jpg"
```

**Result:**

```json
{
  "name": "John",
  "email": "john@example.com",
  "avatar": "https://storage.example.com/avatar.jpg",
  "cover_photo": "https://storage.example.com/cover.jpg"
}
```

### 2. App User Signup

```bash
# Create app user with avatar
curl -X POST "http://localhost:8000/api/auth-collections/signup" \
  -H "x-api-key: your-key" \
  -F "data={\"email\":\"john@example.com\",\"password\":\"pass123\"}" \
  -F "avatar=@profile.jpg"
```

**Result:**

```json
{
  "access_token": "eyJhbGc...",
  "user": {
    "email": "john@example.com",
    "avatar": "https://storage.example.com/avatar.jpg"
  }
}
```

### 3. Update App User Profile

```bash
# Update avatar
curl -X PATCH "http://localhost:8000/api/auth-collections/user" \
  -H "Authorization: Bearer USER_TOKEN" \
  -F "avatar=@new-avatar.jpg"
```

### 4. Product Gallery

```bash
curl -X POST "http://localhost:8000/api/collections/documents?collection=users" \
  -H "x-api-key: your-key" \
  -F "data={\"name\":\"John\",\"email\":\"john@example.com\"}" \
  -F "avatar=@profile.jpg" \
  -F "cover_photo=@cover.jpg"
```

**Result:**

```json
{
  "name": "John",
  "email": "john@example.com",
  "avatar": "https://storage.example.com/avatar.jpg",
  "cover_photo": "https://storage.example.com/cover.jpg"
}
```

### Product Gallery

```bash
curl -X POST "http://localhost:8000/api/collections/documents?collection=products" \
  -H "x-api-key: your-key" \
  -F "data={\"name\":\"Product\",\"price\":99.99}" \
  -F "main_image=@main.jpg" \
  -F "gallery=@img1.jpg" \
  -F "gallery=@img2.jpg" \
  -F "gallery=@img3.jpg"
```

**Result:**

```json
{
  "name": "Product",
  "price": 99.99,
  "main_image": "https://.../main.jpg",
  "gallery": [
    "https://.../img1.jpg",
    "https://.../img2.jpg",
    "https://.../img3.jpg"
  ]
}
```

---

## React Example

### App User Signup

```tsx
import React, { useState } from "react";

function SignUpForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const formData = new FormData();
    formData.append("data", JSON.stringify({ email, password }));

    // Simple! Just name your field
    if (avatarFile) formData.append("avatar", avatarFile);

    const response = await fetch("/api/auth-collections/signup", {
      method: "POST",
      headers: { "x-api-key": "your-key" },
      body: formData,
    });

    const result = await response.json();
    console.log("User created with avatar:", result.user.avatar);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />

      <input
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />

      <input
        type="file"
        onChange={(e) => setAvatarFile(e.target.files?.[0] || null)}
      />

      <button type="submit">Sign Up</button>
    </form>
  );
}
```

### Collection Document

```tsx
function UserForm() {
  const [name, setName] = useState("");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [coverFile, setCoverFile] = useState<File | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const formData = new FormData();
    formData.append("data", JSON.stringify({ name }));

    // Simple! Just name your fields
    if (avatarFile) formData.append("avatar", avatarFile);
    if (coverFile) formData.append("cover_photo", coverFile);

    const response = await fetch(
      "/api/collections/documents?collection=users",
      {
        method: "POST",
        headers: { "x-api-key": "your-key" },
        body: formData,
      }
    );

    const result = await response.json();
    console.log(result);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={name}
        onChange={(e) => setName(e.target.value)}
      />

      <input
        type="file"
        onChange={(e) => setAvatarFile(e.target.files?.[0] || null)}
      />

      <input
        type="file"
        onChange={(e) => setCoverFile(e.target.files?.[0] || null)}
      />

      <button type="submit">Create</button>
    </form>
  );
}
```

---

## How It Works

1. **Named inputs** → Fields

   - `avatar=@file.jpg` → `{ "avatar": "url" }`
   - `cover=@file.jpg` → `{ "cover": "url" }`

2. **Multiple files with same name** → Array

   - `gallery=@img1.jpg gallery=@img2.jpg` → `{ "gallery": ["url1", "url2"] }`

3. **Generic `files` field** → Default behavior
   - `files=@file.jpg` → `{ "file_url": "url" }`
   - `files=@file1.jpg files=@file2.jpg` → `{ "file_urls": ["url1", "url2"] }`

---

## Use Cases

### ✅ Collection Documents

- User profiles in documents
- Product images
- Blog post featured images
- File attachments
- Image galleries

### ✅ App Users

- Profile avatars
- Cover photos
- Verification documents
- ID documents
- Portfolio images

---

## Key Benefits

✅ **Super simple** - just name your input  
✅ **No JSON mapping** required  
✅ **Intuitive** - field name = input name  
✅ **Multiple files** → automatic array  
✅ **Backward compatible** - `files` field still works  
✅ **One request** - no separate upload + create  
✅ **Works everywhere** - documents AND app users

---

## Endpoints

### Collection Documents

- **Create**: `POST /collections/documents?collection={name}`
- **Update**: `PATCH /collections/{collection}/documents/{id}`
- **Auth**: x-api-key header

### App Users

- **Signup**: `POST /auth-collections/signup`
- **Update Profile**: `PATCH /auth-collections/user`
- **Auth**:
  - Signup: x-api-key header (project key)
  - Update: Authorization header (user Bearer token)

---

## Documentation

### Collection Documents

- **[SIMPLE_FILE_UPLOAD_GUIDE.md](./SIMPLE_FILE_UPLOAD_GUIDE.md)** - Complete guide
- **[FILE_UPLOAD_QUICK_REFERENCE.md](./FILE_UPLOAD_QUICK_REFERENCE.md)** - Quick reference
- **[examples/react-simple-file-upload.tsx](./examples/react-simple-file-upload.tsx)** - React examples

### App Users

- **[APP_USER_FILE_UPLOAD_GUIDE.md](./APP_USER_FILE_UPLOAD_GUIDE.md)** - Complete app user guide

---

## Key Benefits

✅ **Super simple** - just name your input  
✅ **No JSON mapping** required  
✅ **Intuitive** - field name = input name  
✅ **Multiple files** → automatic array  
✅ **Backward compatible** - `files` field still works  
✅ **One request** - no separate upload + create

---

## Documentation

- **[SIMPLE_FILE_UPLOAD_GUIDE.md](./SIMPLE_FILE_UPLOAD_GUIDE.md)** - Complete guide
- **[FILE_UPLOAD_QUICK_REFERENCE.md](./FILE_UPLOAD_QUICK_REFERENCE.md)** - Quick reference
- **[examples/react-simple-file-upload.tsx](./examples/react-simple-file-upload.tsx)** - React examples

---

## Migration Guide

### Old Way (2 requests)

```javascript
// 1. Upload file
const uploadRes = await fetch('/collections/file', {...});
const { url } = await uploadRes.json();

// 2. Create document/user
await fetch('/collections/documents', {
  body: JSON.stringify({ data: { name: 'User', avatar: url } })
});
```

### New Way (1 request)

```javascript
const formData = new FormData();
formData.append("data", JSON.stringify({ name: "User" }));
formData.append("avatar", avatarFile); // Just name it!

await fetch("/collections/documents?collection=users", {
  body: formData,
});
```

---

## Common Patterns

```bash
# User profiles (documents)
-F "avatar=@profile.jpg"
-F "cover_photo=@cover.jpg"

# App user signup
-F "avatar=@profile.jpg"

# E-commerce products
-F "avatar=@profile.jpg"
-F "cover_photo=@cover.jpg"

# E-commerce products
-F "main_image=@main.jpg"
-F "gallery=@img1.jpg"
-F "gallery=@img2.jpg"

# Blog posts
-F "featured_image=@hero.jpg"
-F "inline_images=@img1.jpg"
-F "inline_images=@img2.jpg"

# Documents
-F "thumbnail=@thumb.jpg"
-F "attachments=@doc1.pdf"
-F "attachments=@doc2.pdf"
```

---

## Summary

**Upload files in 3 steps:**

1. Create FormData with your data
2. Add files with field names: `formData.append('avatar', file)`
3. Submit!

**Works for:**

- ✅ Collection documents
- ✅ App user profiles

**That's it!** 🎉
