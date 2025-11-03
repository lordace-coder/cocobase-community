# Quick Reference: File Upload with Documents

## 📝 Create Document with Files

### Basic Upload (Auto Field Names)

#### cURL

```bash
curl -X POST "https://api.cocobase.buzz/collections/documents?collection=products" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F 'data={"name":"Product 1","price":99.99}' \
  -F 'files=@image1.jpg' \
  -F 'files=@image2.jpg'
```

### Named File Fields (SIMPLE! ✨)

Just **name your file input** = field name in document!

#### cURL

```bash
# Avatar and cover photo - just name them!
curl -X POST "https://api.cocobase.buzz/collections/documents?collection=users" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F 'data={"name":"John Doe","email":"john@example.com"}' \
  -F 'avatar=@avatar.jpg' \
  -F 'cover_photo=@cover.jpg'
```

**Result:**

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "avatar": "https://.../avatar.jpg",
  "cover_photo": "https://.../cover.jpg"
}
```

#### JavaScript/Fetch

```javascript
const formData = new FormData();
formData.append("data", JSON.stringify({ name: "John Doe" }));

// Simple! Just name your fields
formData.append("avatar", avatarFile);
formData.append("cover_photo", coverFile);

await fetch("/collections/documents?collection=users", {
  method: "POST",
  headers: { Authorization: "Bearer YOUR_API_KEY" },
  body: formData,
});
```

### Multiple Files → Array

```bash
# Multiple files with same name = array
curl -X POST "https://api.cocobase.buzz/collections/documents?collection=products" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F 'data={"name":"Product"}' \
  -F 'gallery=@img1.jpg' \
  -F 'gallery=@img2.jpg' \
  -F 'gallery=@img3.jpg'
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

### JavaScript/Fetch

```javascript
const formData = new FormData();
formData.append("data", JSON.stringify({ name: "Product 1", price: 99.99 }));
formData.append("files", file1);
formData.append("files", file2);

await fetch("/collections/documents?collection=products", {
  method: "POST",
  headers: { Authorization: "Bearer YOUR_API_KEY" },
  body: formData,
});
```

### Python/Requests

```python
import requests

# Simple named fields
files = [
    ('avatar', ('avatar.jpg', open('avatar.jpg', 'rb'), 'image/jpeg')),
    ('cover_photo', ('cover.jpg', open('cover.jpg', 'rb'), 'image/jpeg'))
]

data = {
    'data': '{"name":"John Doe","email":"john@example.com"}'
}

response = requests.post(
    'https://api.cocobase.buzz/collections/documents?collection=users',
    headers={'Authorization': 'Bearer YOUR_API_KEY'},
    data=data,
    files=files
)
```

---

## ✏️ Update Document with Files

### Basic Update

#### cURL

```bash
curl -X PATCH "https://api.cocobase.buzz/collections/products/documents/doc-123" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F 'data={"price":149.99}' \
  -F 'files=@new-image.jpg'
```

### Update Specific Field (SIMPLE!)

```bash
# Update only avatar
curl -X PATCH "https://api.cocobase.buzz/collections/users/documents/user-123" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F 'avatar=@new-avatar.jpg'
```

### JavaScript/Fetch

```javascript
const formData = new FormData();
formData.append("avatar", newAvatarFile); // Just name it!

await fetch("/collections/users/documents/user-123", {
  method: "PATCH",
  headers: { Authorization: "Bearer YOUR_API_KEY" },
  body: formData,
});
```

---

## 📊 Response Format

### Single File (Default)

```json
{
  "id": "doc-123",
  "data": {
    "name": "Product 1",
    "file_url": "https://storage.cocobase.buzz/.../image.jpg"
  }
}
```

### Multiple Files (Default)

```json
{
  "id": "doc-123",
  "data": {
    "name": "Product 1",
    "file_urls": [
      "https://storage.cocobase.buzz/.../image1.jpg",
      "https://storage.cocobase.buzz/.../image2.jpg"
    ]
  }
}
```

### Named File Fields ✨

```json
{
  "id": "user-123",
  "data": {
    "name": "John Doe",
    "avatar": "https://storage.cocobase.buzz/.../avatar.jpg",
    "cover_photo": "https://storage.cocobase.buzz/.../cover.jpg"
  }
}
```

### Array Field (Multiple files with same name)

```json
{
  "id": "product-456",
  "data": {
    "name": "Laptop",
    "gallery": [
      "https://storage.cocobase.buzz/.../image1.jpg",
      "https://storage.cocobase.buzz/.../image2.jpg",
      "https://storage.cocobase.buzz/.../image3.jpg"
    ]
  }
}
```

---

## ⚡ Quick Tips

1. **Don't set Content-Type header** - Browser does it automatically
2. **Files are stored** in `projects/{project_id}/{collection_name}/`
3. **Simple named fields**:
   - Input name = field name
   - `avatar=@file.jpg` → `{"avatar": "url"}`
   - Same name multiple times → array
4. **Default behavior** (generic `files` field):
   - Single file → `file_url` (string)
   - Multiple files → `file_urls` (array)
5. **Updates merge data** - existing fields preserved
6. **Storage limits** enforced based on pricing plan

---

## 🎯 Common Patterns

### User Profile

```bash
-F 'avatar=@profile.jpg' \
-F 'cover_photo=@cover.jpg'
```

### Product with Gallery

```bash
-F 'main_image=@main.jpg' \
-F 'gallery=@img1.jpg' \
-F 'gallery=@img2.jpg' \
-F 'gallery=@img3.jpg'
```

### Blog Post

```bash
-F 'featured_image=@hero.jpg' \
-F 'inline_images=@img1.jpg' \
-F 'inline_images=@img2.jpg'
```

---

## 🔄 Migration

### Before (2 requests)

```javascript
// 1. Upload file
const uploadRes = await fetch('/collections/file', {...});
const { url } = await uploadRes.json();

// 2. Create document
await fetch('/collections/documents?collection=products', {
  body: JSON.stringify({ data: { name: 'Product', image: url } })
});
```

### After (1 request - Simple!)

```javascript
const formData = new FormData();
formData.append("data", JSON.stringify({ name: "Product" }));
formData.append("product_image", imageFile); // Just name it!

await fetch("/collections/documents?collection=products", {
  body: formData,
});
// Result: { name: "Product", product_image: "https://..." }
```

---

## 📚 See Also

- **[SIMPLE_FILE_UPLOAD_GUIDE.md](./SIMPLE_FILE_UPLOAD_GUIDE.md)** - Complete guide with examples
- **[FILE_UPLOAD_WITH_DOCUMENTS.md](./FILE_UPLOAD_WITH_DOCUMENTS.md)** - Detailed implementation
