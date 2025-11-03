# Quick Reference: File Upload with Documents

## 📝 Create Document with Files

### cURL

```bash
curl -X POST "https://api.cocobase.com/collections/documents?collection=products" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F 'data={"name":"Product 1","price":99.99}' \
  -F 'files=@image1.jpg' \
  -F 'files=@image2.jpg'
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

## ✏️ Update Document with Files

### cURL

```bash
curl -X PATCH "https://api.cocobase.com/collections/products/documents/doc-123" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F 'data={"price":149.99}' \
  -F 'files=@new-image.jpg'
```

### JavaScript/Fetch

```javascript
const formData = new FormData();
formData.append("data", JSON.stringify({ price: 149.99 }));
formData.append("files", newFile);

await fetch("/collections/products/documents/doc-123", {
  method: "PATCH",
  headers: { Authorization: "Bearer YOUR_API_KEY" },
  body: formData,
});
```

---

## 📊 Response Format

### Single File

```json
{
  "id": "doc-123",
  "data": {
    "name": "Product 1",
    "file_url": "https://storage.cocobase.com/.../image.jpg"
  }
}
```

### Multiple Files

```json
{
  "id": "doc-123",
  "data": {
    "name": "Product 1",
    "file_urls": [
      "https://storage.cocobase.com/.../image1.jpg",
      "https://storage.cocobase.com/.../image2.jpg"
    ]
  }
}
```

---

## ⚡ Quick Tips

1. **Don't set Content-Type header** - Browser does it automatically
2. **Files are stored** in `projects/{project_id}/{collection_name}/`
3. **Single file** → `file_url` (string)
4. **Multiple files** → `file_urls` (array)
5. **Updates append** to `file_urls` array (preserves existing)
6. **Storage limits** enforced based on pricing plan

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

### After (1 request)

```javascript
const formData = new FormData();
formData.append("data", JSON.stringify({ name: "Product" }));
formData.append("files", imageFile);

await fetch("/collections/documents?collection=products", {
  body: formData,
});
```
