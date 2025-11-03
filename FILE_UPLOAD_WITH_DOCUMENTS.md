# File Upload with Document Creation/Update

## 🎯 Overview

You can now upload files **directly** when creating or updating collection documents! The file URLs are automatically stored as fields in the document data.

**Benefits:**

- ✅ No need for separate upload + create operations
- ✅ File URLs automatically stored in document
- ✅ Supports single or multiple files
- ✅ Atomic operation (all or nothing)
- ✅ Files organized by collection name
- ✅ Storage limits automatically checked

---

## 📝 Create Document with Files

### Endpoint

```
POST /collections/documents?collection={collection_name}
```

### Request Types

#### 1. JSON Only (No Files)

**Traditional approach - still works!**

```bash
curl -X POST "https://api.cocobase.com/collections/documents?collection=products" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "name": "Product 1",
      "price": 99.99,
      "description": "A great product"
    }
  }'
```

---

#### 2. With File Upload (Multipart Form-Data)

**NEW: Upload files while creating document!**

```bash
curl -X POST "https://api.cocobase.com/collections/documents?collection=products" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F 'data={"name":"Product 1","price":99.99}' \
  -F 'files=@product-image.jpg' \
  -F 'files=@product-thumbnail.jpg'
```

**Response:**

```json
{
  "id": "doc-abc123",
  "collection_id": "col-xyz789",
  "created_at": "2024-01-15T10:30:00Z",
  "data": {
    "name": "Product 1",
    "price": 99.99,
    "file_urls": [
      "https://storage.cocobase.com/projects/proj-123/products/product-image.jpg",
      "https://storage.cocobase.com/projects/proj-123/products/product-thumbnail.jpg"
    ]
  }
}
```

---

### File Field Naming

#### Single File

If you upload **1 file**, it's stored as `file_url` (string):

```json
{
  "name": "Product 1",
  "file_url": "https://storage.cocobase.com/.../image.jpg"
}
```

#### Multiple Files

If you upload **2+ files**, they're stored as `file_urls` (array):

```json
{
  "name": "Product 1",
  "file_urls": [
    "https://storage.cocobase.com/.../image1.jpg",
    "https://storage.cocobase.com/.../image2.jpg"
  ]
}
```

---

### JavaScript Examples

#### Using Fetch API

```javascript
// Create FormData
const formData = new FormData();

// Add JSON data
formData.append(
  "data",
  JSON.stringify({
    name: "Product 1",
    price: 99.99,
    category: "electronics",
  })
);

// Add files
const fileInput = document.querySelector("#file-input");
for (const file of fileInput.files) {
  formData.append("files", file);
}

// Upload
const response = await fetch(
  "https://api.cocobase.com/collections/documents?collection=products",
  {
    method: "POST",
    headers: {
      Authorization: "Bearer YOUR_API_KEY",
    },
    body: formData,
  }
);

const result = await response.json();
console.log("Created:", result);
```

---

#### Using Axios

```javascript
import axios from "axios";

const formData = new FormData();

// Add data
formData.append(
  "data",
  JSON.stringify({
    name: "Product 1",
    price: 99.99,
  })
);

// Add files
formData.append("files", file1);
formData.append("files", file2);

const response = await axios.post(
  "https://api.cocobase.com/collections/documents?collection=products",
  formData,
  {
    headers: {
      Authorization: "Bearer YOUR_API_KEY",
      "Content-Type": "multipart/form-data",
    },
  }
);

console.log("Created:", response.data);
```

---

## ✏️ Update Document with Files

### Endpoint

```
PATCH /collections/{collection}/documents/{document_id}
```

### Update Behavior

#### 1. Update Data Only

```bash
curl -X PATCH "https://api.cocobase.com/collections/products/documents/doc-123" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "price": 149.99
    }
  }'
```

---

#### 2. Upload New Files

```bash
curl -X PATCH "https://api.cocobase.com/collections/products/documents/doc-123" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F 'files=@new-image.jpg'
```

**Before:**

```json
{
  "name": "Product 1",
  "price": 99.99,
  "file_url": "https://storage.cocobase.com/.../old-image.jpg"
}
```

**After:**

```json
{
  "name": "Product 1",
  "price": 99.99,
  "file_url": "https://storage.cocobase.com/.../new-image.jpg"
}
```

---

#### 3. Upload Multiple New Files (Preserves Existing)

```bash
curl -X PATCH "https://api.cocobase.com/collections/products/documents/doc-123" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F 'files=@image3.jpg' \
  -F 'files=@image4.jpg'
```

**Before:**

```json
{
  "name": "Product 1",
  "file_urls": [
    "https://storage.cocobase.com/.../image1.jpg",
    "https://storage.cocobase.com/.../image2.jpg"
  ]
}
```

**After (appends new files):**

```json
{
  "name": "Product 1",
  "file_urls": [
    "https://storage.cocobase.com/.../image1.jpg", // Preserved
    "https://storage.cocobase.com/.../image2.jpg", // Preserved
    "https://storage.cocobase.com/.../image3.jpg", // Added
    "https://storage.cocobase.com/.../image4.jpg" // Added
  ]
}
```

---

#### 4. Update Data + Upload Files

```bash
curl -X PATCH "https://api.cocobase.com/collections/products/documents/doc-123" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -F 'data={"name":"Updated Product","price":149.99}' \
  -F 'files=@new-image.jpg'
```

---

### JavaScript Update Example

```javascript
const formData = new FormData();

// Update some fields
formData.append(
  "data",
  JSON.stringify({
    name: "Updated Product",
    price: 149.99,
  })
);

// Add new images
formData.append("files", newImage1);
formData.append("files", newImage2);

const response = await fetch(
  "https://api.cocobase.com/collections/products/documents/doc-123",
  {
    method: "PATCH",
    headers: {
      Authorization: "Bearer YOUR_API_KEY",
    },
    body: formData,
  }
);

const result = await response.json();
console.log("Updated:", result);
```

---

## 🗂️ File Organization

Files are stored with this structure:

```
projects/{project_id}/{collection_name}/{filename}
```

**Example:**

```
projects/proj-abc123/products/laptop-image.jpg
projects/proj-abc123/users/avatar.png
projects/proj-abc123/posts/banner.jpg
```

**Benefits:**

- ✅ Files organized by collection
- ✅ Easy to identify which collection files belong to
- ✅ Easier cleanup if collection is deleted
- ✅ Better performance for listing collection files

---

## 📊 Real-World Use Cases

### 1. Product Management

```javascript
// Create product with images
const formData = new FormData();
formData.append(
  "data",
  JSON.stringify({
    name: "Gaming Laptop",
    price: 1299.99,
    category: "electronics",
    specs: {
      ram: "16GB",
      storage: "512GB SSD",
    },
  })
);

formData.append("files", productImage);
formData.append("files", thumbnailImage);

await fetch("/collections/documents?collection=products", {
  method: "POST",
  body: formData,
});
```

**Result:**

```json
{
  "id": "prod-123",
  "data": {
    "name": "Gaming Laptop",
    "price": 1299.99,
    "category": "electronics",
    "specs": {...},
    "file_urls": [
      "https://.../laptop-front.jpg",
      "https://.../laptop-thumbnail.jpg"
    ]
  }
}
```

---

### 2. User Profiles with Avatar

```javascript
// Upload avatar with user data
const formData = new FormData();
formData.append(
  "data",
  JSON.stringify({
    name: "John Doe",
    email: "john@example.com",
    bio: "Software developer",
  })
);

formData.append("files", avatarFile);

await fetch("/collections/documents?collection=users", {
  method: "POST",
  body: formData,
});
```

**Result:**

```json
{
  "id": "user-456",
  "data": {
    "name": "John Doe",
    "email": "john@example.com",
    "bio": "Software developer",
    "file_url": "https://.../avatar.jpg"
  }
}
```

---

### 3. Blog Post with Cover Image

```javascript
const formData = new FormData();
formData.append(
  "data",
  JSON.stringify({
    title: "Getting Started with CocoBase",
    content: "Lorem ipsum...",
    author_id: "user-123",
    tags: ["tutorial", "beginner"],
  })
);

formData.append("files", coverImage);

await fetch("/collections/documents?collection=posts", {
  method: "POST",
  body: formData,
});
```

---

### 4. Document Attachments

```javascript
// Create document with multiple attachments
const formData = new FormData();
formData.append(
  "data",
  JSON.stringify({
    title: "Project Proposal",
    description: "Q1 2024 Initiative",
    status: "draft",
  })
);

formData.append("files", pdfFile);
formData.append("files", spreadsheet);
formData.append("files", presentationFile);

await fetch("/collections/documents?collection=proposals", {
  method: "POST",
  body: formData,
});
```

**Result:**

```json
{
  "id": "doc-789",
  "data": {
    "title": "Project Proposal",
    "description": "Q1 2024 Initiative",
    "status": "draft",
    "file_urls": [
      "https://.../proposal.pdf",
      "https://.../budget.xlsx",
      "https://.../slides.pptx"
    ]
  }
}
```

---

## 🔒 Storage Limits

File uploads automatically check your project's storage limit based on your pricing plan.

**Limits:**

- Free Plan: 50MB total storage
- Pro Plan: 500MB total storage
- Enterprise: Custom limits

**Error Response (Limit Exceeded):**

```json
{
  "detail": "Storage limit exceeded. Current: 48.5MB, Limit: 50MB"
}
```

**What Happens:**

1. System calculates current project storage usage
2. Checks if new file would exceed limit
3. Rejects upload if over limit
4. Sends notification to project users
5. Document creation/update is rolled back (no partial data)

---

## 🎨 Custom Field Names

By default, files are stored as `file_url` or `file_urls`. But you can customize this!

### Option 1: Rename After Upload

```javascript
// Upload first
const formData = new FormData();
formData.append(
  "data",
  JSON.stringify({
    name: "Product",
  })
);
formData.append("files", image);

const response = await fetch("/collections/documents?collection=products", {
  method: "POST",
  body: formData,
});

const doc = await response.json();

// Then update field names
await fetch(`/collections/products/documents/${doc.id}`, {
  method: "PATCH",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    data: {
      image_url: doc.data.file_url, // Rename
      file_url: null, // Remove old field
    },
  }),
});
```

---

### Option 2: Upload Separately with Custom Names

```javascript
// 1. Upload file first
const fileFormData = new FormData();
fileFormData.append("file", imageFile);

const uploadResponse = await fetch("/collections/file", {
  method: "POST",
  body: fileFormData,
});

const { url } = await uploadResponse.json();

// 2. Create document with custom field name
await fetch("/collections/documents?collection=products", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    data: {
      name: "Product",
      primary_image: url, // ← Custom name
      thumbnail: url, // ← Another custom name
      gallery: [url, url], // ← Array with custom name
    },
  }),
});
```

---

## 🔄 Migration from Separate Uploads

### Before (Two Steps):

```javascript
// Step 1: Upload file
const fileData = new FormData();
fileData.append("file", imageFile);

const uploadRes = await fetch("/collections/file", {
  method: "POST",
  body: fileData,
});

const { url } = await uploadRes.json();

// Step 2: Create document
await fetch("/collections/documents?collection=products", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    data: {
      name: "Product",
      image_url: url, // Manually add URL
    },
  }),
});
```

---

### After (One Step):

```javascript
// Single request!
const formData = new FormData();
formData.append(
  "data",
  JSON.stringify({
    name: "Product",
  })
);
formData.append("files", imageFile);

await fetch("/collections/documents?collection=products", {
  method: "POST",
  body: formData,
});
```

**Benefits:**

- ⚡ Faster (one request vs two)
- ✅ Atomic (all or nothing)
- 🎯 Simpler code
- 🔒 No orphaned files

---

## 📱 React Example

```jsx
import { useState } from "react";

function ProductForm() {
  const [formData, setFormData] = useState({
    name: "",
    price: "",
  });
  const [files, setFiles] = useState([]);

  const handleSubmit = async (e) => {
    e.preventDefault();

    const data = new FormData();

    // Add JSON data
    data.append("data", JSON.stringify(formData));

    // Add files
    files.forEach((file) => {
      data.append("files", file);
    });

    try {
      const response = await fetch(
        "https://api.cocobase.com/collections/documents?collection=products",
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${API_KEY}`,
          },
          body: data,
        }
      );

      const result = await response.json();
      console.log("Created:", result);

      // Success! File URLs are in result.data.file_urls
    } catch (error) {
      console.error("Error:", error);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Product Name"
        value={formData.name}
        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
      />

      <input
        type="number"
        placeholder="Price"
        value={formData.price}
        onChange={(e) => setFormData({ ...formData, price: e.target.value })}
      />

      <input
        type="file"
        multiple
        onChange={(e) => setFiles(Array.from(e.target.files))}
      />

      <button type="submit">Create Product</button>
    </form>
  );
}
```

---

## ⚠️ Important Notes

### 1. Content-Type Header

**When uploading files, DO NOT set Content-Type header manually!**

```javascript
// ❌ WRONG
fetch(url, {
  headers: {
    "Content-Type": "multipart/form-data", // DON'T DO THIS!
  },
  body: formData,
});

// ✅ CORRECT
fetch(url, {
  // No Content-Type header - browser sets it automatically with boundary
  body: formData,
});
```

The browser automatically sets `Content-Type: multipart/form-data; boundary=...` with the correct boundary string.

---

### 2. Data Merging

Updates **merge** with existing data, they don't replace it:

```javascript
// Before:
{ name: 'Product', price: 99, category: 'electronics' }

// Update with:
{ price: 149 }

// After:
{ name: 'Product', price: 149, category: 'electronics' }
//   ^^ Preserved    ^^ Updated    ^^ Preserved
```

---

### 3. File Arrays

When updating with multiple files, **new files are appended** to `file_urls`:

```javascript
// Before:
{
  file_urls: ["url1", "url2"];
}

// Upload 2 more files

// After:
{
  file_urls: ["url1", "url2", "url3", "url4"];
}
```

To replace files, you need to manually update the field:

```javascript
// Upload new files
// Then update:
await fetch(`/collections/products/documents/${id}`, {
  method: "PATCH",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    data: {
      file_urls: ["new-url-only"], // Replace entire array
    },
  }),
});
```

---

### 4. File Validation

Currently, the API doesn't validate file types or names. Best practices:

```javascript
// Client-side validation
const allowedTypes = ["image/jpeg", "image/png", "image/gif"];
const maxSize = 5 * 1024 * 1024; // 5MB

function validateFile(file) {
  if (!allowedTypes.includes(file.type)) {
    throw new Error("Invalid file type");
  }

  if (file.size > maxSize) {
    throw new Error("File too large");
  }

  return true;
}
```

---

## 🎯 Summary

**Key Features:**

- ✅ Upload files during document create/update
- ✅ Single or multiple files supported
- ✅ Automatic URL storage in document
- ✅ Files organized by collection name
- ✅ Storage limits enforced
- ✅ Data merging (not replacement)
- ✅ Atomic operations (all or nothing)

**Use When:**

- Creating products with images
- User profiles with avatars
- Blog posts with cover images
- Documents with attachments
- Any record that needs associated files

**Avoid When:**

- You need custom field names (use separate upload)
- Files are large and should upload in background
- You want fine-grained control over storage paths
