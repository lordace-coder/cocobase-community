# App User File Upload Guide

## 🎯 Upload Files for User Profiles

Upload profile pictures, cover photos, and other files when creating or updating app users!

---

## Creating App User with Files

### Basic Example (Avatar + Cover Photo)

```bash
curl -X POST "http://localhost:8000/api/auth-collections/signup" \
  -H "x-api-key: your-project-key" \
  -F "data={\"email\":\"john@example.com\",\"password\":\"securepass123\",\"username\":\"johndoe\"}" \
  -F "avatar=@profile-pic.jpg" \
  -F "cover_photo=@cover-image.jpg"
```

**Response:**

```json
{
  "access_token": "eyJhbGc...",
  "user": {
    "id": "user-123",
    "email": "john@example.com",
    "username": "johndoe",
    "avatar": "https://storage.example.com/.../profile-pic.jpg",
    "cover_photo": "https://storage.example.com/.../cover-image.jpg"
  }
}
```

---

## Updating Current User with Files

### Update Avatar Only

```bash
curl -X PATCH "http://localhost:8000/api/auth-collections/user" \
  -H "Authorization: Bearer YOUR_USER_TOKEN" \
  -F "avatar=@new-avatar.jpg"
```

### Update Multiple Fields + Files

```bash
curl -X PATCH "http://localhost:8000/api/auth-collections/user" \
  -H "Authorization: Bearer YOUR_USER_TOKEN" \
  -F "data={\"username\":\"newtusername\",\"bio\":\"Updated bio\"}" \
  -F "avatar=@new-avatar.jpg" \
  -F "cover_photo=@new-cover.jpg"
```

---

## JavaScript/Fetch Examples

### Sign Up with Avatar

```javascript
const formData = new FormData();

// User data
formData.append(
  "data",
  JSON.stringify({
    email: "john@example.com",
    password: "securepass123",
    username: "johndoe",
    full_name: "John Doe",
  })
);

// Profile picture
formData.append("avatar", avatarFile);
formData.append("cover_photo", coverFile);

const response = await fetch(
  "http://localhost:8000/api/auth-collections/signup",
  {
    method: "POST",
    headers: {
      "x-api-key": "your-project-key",
    },
    body: formData,
  }
);

const result = await response.json();
console.log("User created:", result);
console.log("Avatar URL:", result.user.avatar);
```

### Update Profile Picture

```javascript
const formData = new FormData();
formData.append("avatar", newAvatarFile);

const response = await fetch(
  "http://localhost:8000/api/auth-collections/user",
  {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${userToken}`,
    },
    body: formData,
  }
);

const updatedUser = await response.json();
console.log("New avatar:", updatedUser.avatar);
```

---

## React Component Example

```tsx
import React, { useState } from "react";

function SignUpForm() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [username, setUsername] = useState("");
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [coverFile, setCoverFile] = useState<File | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const formData = new FormData();

    // User data
    formData.append(
      "data",
      JSON.stringify({
        email,
        password,
        username,
      })
    );

    // Files - just name them!
    if (avatarFile) formData.append("avatar", avatarFile);
    if (coverFile) formData.append("cover_photo", coverFile);

    try {
      const response = await fetch(
        "http://localhost:8000/api/auth-collections/signup",
        {
          method: "POST",
          headers: {
            "x-api-key": "your-project-key",
          },
          body: formData,
        }
      );

      const result = await response.json();
      console.log("User created:", result);

      // Store the token
      localStorage.setItem("token", result.access_token);

      alert("Sign up successful!");
    } catch (error) {
      console.error("Sign up failed:", error);
      alert("Sign up failed. Please try again.");
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        placeholder="Email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        required
      />

      <input
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />

      <input
        type="text"
        placeholder="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        required
      />

      <label>
        Profile Picture:
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

      <button type="submit">Sign Up</button>
    </form>
  );
}

function UpdateProfileButton({ userToken }: { userToken: string }) {
  const handleAvatarUpdate = async (file: File) => {
    const formData = new FormData();
    formData.append("avatar", file);

    try {
      const response = await fetch(
        "http://localhost:8000/api/auth-collections/user",
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${userToken}`,
          },
          body: formData,
        }
      );

      const updatedUser = await response.json();
      console.log("Profile updated:", updatedUser);
      alert("Avatar updated successfully!");
    } catch (error) {
      console.error("Update failed:", error);
      alert("Failed to update avatar");
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      handleAvatarUpdate(file);
    }
  };

  return (
    <label className="cursor-pointer">
      Change Avatar
      <input
        type="file"
        accept="image/*"
        onChange={handleFileSelect}
        style={{ display: "none" }}
      />
    </label>
  );
}
```

---

## Python Example

### Sign Up with Avatar

```python
import requests
import json

url = "http://localhost:8000/api/auth-collections/signup"
headers = {"x-api-key": "your-project-key"}

# User data
data = {
    "data": (None, json.dumps({
        "email": "john@example.com",
        "password": "securepass123",
        "username": "johndoe"
    }))
}

# Files
files = [
    ("avatar", ("avatar.jpg", open("avatar.jpg", "rb"), "image/jpeg")),
    ("cover_photo", ("cover.jpg", open("cover.jpg", "rb"), "image/jpeg"))
]

response = requests.post(url, headers=headers, data=data, files=files)
result = response.json()

print("User created:", result)
print("Avatar URL:", result["user"]["avatar"])
```

### Update Profile

```python
import requests

url = "http://localhost:8000/api/auth-collections/user"
headers = {"Authorization": f"Bearer {user_token}"}

files = [
    ("avatar", ("new-avatar.jpg", open("new-avatar.jpg", "rb"), "image/jpeg"))
]

response = requests.patch(url, headers=headers, files=files)
updated_user = response.json()

print("Updated avatar:", updated_user["avatar"])
```

---

## Field Names

### Common User Profile Fields

```bash
# Profile images
-F "avatar=@profile.jpg"
-F "cover_photo=@cover.jpg"
-F "profile_picture=@pic.jpg"

# Documents/verification
-F "id_document=@id.jpg"
-F "verification_photo=@verification.jpg"

# Multiple images
-F "gallery=@img1.jpg"
-F "gallery=@img2.jpg"
-F "gallery=@img3.jpg"
```

---

## How It Works

1. **Name your file input** = field name in user record
2. Files are uploaded to storage
3. URLs are automatically stored in user fields
4. Works for both **signup** and **profile updates**

### Storage Location

Files are stored in: `projects/{project_id}/users/{filename}`

---

## Authentication

### Sign Up (POST /auth-collections/signup)

- **Auth**: Project API key (x-api-key header)
- **Returns**: User access token

### Update Profile (PATCH /auth-collections/user)

- **Auth**: User Bearer token (Authorization header)
- **Returns**: Updated user object

---

## Response Format

### Sign Up Response

```json
{
  "access_token": "eyJhbGc...",
  "user": {
    "id": "user-123",
    "email": "john@example.com",
    "username": "johndoe",
    "avatar": "https://storage.example.com/.../avatar.jpg",
    "cover_photo": "https://storage.example.com/.../cover.jpg",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### Update Response

```json
{
  "id": "user-123",
  "email": "john@example.com",
  "username": "johndoe",
  "avatar": "https://storage.example.com/.../new-avatar.jpg",
  "bio": "Updated bio",
  "updated_at": "2024-01-15T14:20:00Z"
}
```

---

## Best Practices

1. **Validate file types** on frontend before upload
2. **Compress images** to save storage and bandwidth
3. **Show upload progress** for better UX
4. **Handle errors gracefully** (storage limits, file size, etc.)
5. **Display avatars** with fallback images

---

## Error Handling

### Storage Limit Exceeded

```json
{
  "detail": "Storage limit exceeded. Current: 48MB, Limit: 50MB"
}
```

### Invalid File Format

```json
{
  "detail": "Invalid file format. Supported: jpg, png, gif, webp"
}
```

### Unauthorized

```json
{
  "detail": "Not authenticated"
}
```

---

## Complete Example: User Profile Form

```tsx
import React, { useState } from "react";

function UserProfileSetup() {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    username: "",
    full_name: "",
    bio: "",
  });
  const [avatarFile, setAvatarFile] = useState<File | null>(null);
  const [avatarPreview, setAvatarPreview] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleAvatarChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setAvatarFile(file);
      // Show preview
      const reader = new FileReader();
      reader.onloadend = () => {
        setAvatarPreview(reader.result as string);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const data = new FormData();
      data.append("data", JSON.stringify(formData));

      if (avatarFile) {
        data.append("avatar", avatarFile);
      }

      const response = await fetch("/api/auth-collections/signup", {
        method: "POST",
        headers: { "x-api-key": "your-project-key" },
        body: data,
      });

      if (!response.ok) {
        throw new Error("Sign up failed");
      }

      const result = await response.json();
      localStorage.setItem("token", result.access_token);

      alert("Sign up successful!");
      // Redirect to dashboard or home
    } catch (error) {
      console.error("Error:", error);
      alert("Sign up failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-md mx-auto p-6">
      <h2 className="text-2xl font-bold mb-6">Create Your Profile</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Avatar Preview */}
        {avatarPreview && (
          <div className="flex justify-center mb-4">
            <img
              src={avatarPreview}
              alt="Avatar preview"
              className="w-24 h-24 rounded-full object-cover"
            />
          </div>
        )}

        {/* Avatar Upload */}
        <div>
          <label className="block text-sm font-medium mb-2">
            Profile Picture
          </label>
          <input
            type="file"
            accept="image/*"
            onChange={handleAvatarChange}
            className="w-full"
          />
        </div>

        {/* Form fields */}
        <input
          type="text"
          placeholder="Full Name"
          value={formData.full_name}
          onChange={(e) =>
            setFormData({ ...formData, full_name: e.target.value })
          }
          className="w-full px-3 py-2 border rounded"
        />

        <input
          type="text"
          placeholder="Username"
          value={formData.username}
          onChange={(e) =>
            setFormData({ ...formData, username: e.target.value })
          }
          required
          className="w-full px-3 py-2 border rounded"
        />

        <input
          type="email"
          placeholder="Email"
          value={formData.email}
          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          required
          className="w-full px-3 py-2 border rounded"
        />

        <input
          type="password"
          placeholder="Password"
          value={formData.password}
          onChange={(e) =>
            setFormData({ ...formData, password: e.target.value })
          }
          required
          className="w-full px-3 py-2 border rounded"
        />

        <textarea
          placeholder="Bio (optional)"
          value={formData.bio}
          onChange={(e) => setFormData({ ...formData, bio: e.target.value })}
          rows={3}
          className="w-full px-3 py-2 border rounded"
        />

        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
        >
          {loading ? "Creating Account..." : "Sign Up"}
        </button>
      </form>
    </div>
  );
}

export default UserProfileSetup;
```

---

## Summary

✅ **Simple**: Just name your file inputs (avatar, cover_photo, etc.)  
✅ **Works on signup**: Upload profile pics during registration  
✅ **Works on updates**: Change avatar/cover photo anytime  
✅ **Automatic storage**: Files uploaded to project storage  
✅ **URL returned**: Get file URLs in response  
✅ **Storage limits**: Enforced based on your plan

Perfect for user profiles, avatars, cover photos, verification documents, and more! 🚀
