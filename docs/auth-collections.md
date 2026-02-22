# Auth Collections API

User authentication and management for your application.

**Base URL:** `https://api.cocobase.buzz/auth-collections`

---

## Table of Contents

1. [Authentication](#authentication)
2. [Sign Up](#sign-up)
3. [Login](#login)
4. [Get Current User](#get-current-user)
5. [Update User](#update-user)
6. [List Users](#list-users)
7. [Get User by ID](#get-user-by-id)
8. [OAuth Authentication](#oauth-authentication)
9. [User Relationships](#user-relationships)

---

## Authentication

Auth collections use **two types of authentication**:

### 1. API Key (Project Access)
For administrative operations (list users, get user by ID):
```bash
-H "X-API-Key: your-api-key"
```

### 2. JWT Token (User Access)
For user-specific operations (get current user, update profile):
```bash
-H "Authorization: Bearer jwt-token-here"
```

---

## Sign Up

Create a new user account with email and password.

**Endpoint:** `POST /auth-collections/signup`

**Headers:**
```bash
X-API-Key: your-api-key
Content-Type: application/json
```

### Basic Sign Up

```bash
curl -X POST https://api.cocobase.buzz/auth-collections/signup \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "secure_password_123",
    "data": {
      "username": "johndoe",
      "full_name": "John Doe",
      "age": 25
    }
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### Sign Up with File Upload

```bash
curl -X POST https://api.cocobase.buzz/auth-collections/signup \
  -H "X-API-Key: your-api-key" \
  -F 'data={"email":"john@example.com","password":"secure_password_123","data":{"username":"johndoe"}}' \
  -F "profile_picture=@/path/to/image.jpg"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Notes:**
- Email and password are required
- Password is automatically hashed (bcrypt)
- Additional user data goes in the `data` field (any JSON structure)
- Files are uploaded to S3 and URLs are stored in `data`
- Returns JWT token immediately after signup

---

## Login

Authenticate existing user with email and password.

**Endpoint:** `POST /auth-collections/login`

**Headers:**
```bash
X-API-Key: your-api-key
Content-Type: application/json
```

**Example:**
```bash
curl -X POST https://api.cocobase.buzz/auth-collections/login \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "secure_password_123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Error Responses:**

```json
// User not found
{
  "detail": "Account with this email does not exist"
}

// Wrong password
{
  "detail": "Invalid password value"
}
```

---

## Get Current User

Get the authenticated user's profile.

**Endpoint:** `GET /auth-collections/user`

**Headers:**
```bash
Authorization: Bearer your-jwt-token
```

**Example:**
```bash
curl https://api.cocobase.buzz/auth-collections/user \
  -H "Authorization: Bearer your-jwt-token"
```

**Response:**
```json
{
  "id": "user_abc123",
  "email": "john@example.com",
  "data": {
    "username": "johndoe",
    "full_name": "John Doe",
    "age": 25,
    "profile_picture": "https://storage.url/image.jpg"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "oauth_id": null,
  "roles": ["user"]
}
```

---

## Update User

Update the authenticated user's profile.

**Endpoint:** `PATCH /auth-collections/user`

**Headers:**
```bash
Authorization: Bearer your-jwt-token
Content-Type: application/json
```

### Update Profile Data

```bash
curl -X PATCH https://api.cocobase.buzz/auth-collections/user \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "username": "john_doe_updated",
      "bio": "Software developer"
    }
  }'
```

### Array Operations on User Data (NEW!)

Manage array fields in user data (like followers, interests, bookmarks) without replacing the entire array.

#### Follow a User

```bash
curl -X PATCH https://api.cocobase.buzz/auth-collections/user \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "$append": {
      "following": ["user_456"]
    }
  }'
```

#### Unfollow a User

```bash
curl -X PATCH https://api.cocobase.buzz/auth-collections/user \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "$remove": {
      "following": ["user_456"]
    }
  }'
```

#### Combined Operations

Update profile and manage arrays in one request:

```bash
curl -X PATCH https://api.cocobase.buzz/auth-collections/user \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newemail@example.com",
    "data": {
      "bio": "Updated bio"
    },
    "$append": {
      "followers": ["user_789"],
      "interests": ["programming", "ai"]
    },
    "$remove": {
      "blocked_users": ["user_123"]
    }
  }'
```

**JavaScript Example - Follow/Unfollow:**
```javascript
// Follow a user
await fetch('https://api.cocobase.buzz/auth-collections/user', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    $append: {
      following: ['user_456']
    }
  })
});

// Unfollow a user
await fetch('https://api.cocobase.buzz/auth-collections/user', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    $remove: {
      following: ['user_456']
    }
  })
});
```

**Notes:**
- Array operations work on fields within the `data` JSONB field
- Top-level fields like `email` are updated normally
- `$append` creates arrays automatically if they don't exist
- `$append` prevents duplicate entries
- `$remove` safely handles missing fields
- Operations execute in order: remove → append → regular updates

### Update with File Upload

```bash
curl -X PATCH https://api.cocobase.buzz/auth-collections/user \
  -H "Authorization: Bearer your-jwt-token" \
  -F 'data={"data":{"bio":"Updated bio"}}' \
  -F "profile_picture=@/path/to/new-image.jpg"
```

### Change Password

```bash
curl -X PATCH https://api.cocobase.buzz/auth-collections/user \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "password": "new_secure_password_456"
  }'
```

**Response:**
```json
{
  "id": "user_abc123",
  "email": "john@example.com",
  "data": {
    "username": "john_doe_updated",
    "bio": "Software developer"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "oauth_id": null,
  "roles": ["user"]
}
```

---

## List Users

Get all users with advanced filtering, sorting, and pagination.

**Endpoint:** `GET /auth-collections/users`

**Headers:**
```bash
X-API-Key: your-api-key
```

### Basic Query

```bash
curl "https://api.cocobase.buzz/auth-collections/users" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "data": [
    {
      "id": "user_abc123",
      "email": "john@example.com",
      "data": {
        "username": "johndoe",
        "age": 25
      },
      "created_at": "2024-01-15T10:30:00Z",
      "oauth_id": null,
      "roles": ["user"]
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0,
  "has_more": false
}
```

### Filter by Email

```bash
curl "https://api.cocobase.buzz/auth-collections/users?email_contains=gmail" \
  -H "X-API-Key: your-api-key"
```

### Filter by JSONB Data Fields

```bash
# Find users by username
curl "https://api.cocobase.buzz/auth-collections/users?data.username=johndoe" \
  -H "X-API-Key: your-api-key"

# Find users over 18
curl "https://api.cocobase.buzz/auth-collections/users?data.age_gte=18" \
  -H "X-API-Key: your-api-key"

# Find admins or moderators
curl "https://api.cocobase.buzz/auth-collections/users?data.role_in=admin,moderator" \
  -H "X-API-Key: your-api-key"
```

### OR Conditions

```bash
# Find admins OR moderators
curl "https://api.cocobase.buzz/auth-collections/users?[or]data.role=admin&[or]data.role=moderator" \
  -H "X-API-Key: your-api-key"
```

### Multi-Field Search

```bash
# Search in email OR username
curl "https://api.cocobase.buzz/auth-collections/users?email__or__data.username_contains=john" \
  -H "X-API-Key: your-api-key"
```

### Sorting

```bash
# Sort by email
curl "https://api.cocobase.buzz/auth-collections/users?sort=email&order=asc" \
  -H "X-API-Key: your-api-key"

# Sort by JSONB field
curl "https://api.cocobase.buzz/auth-collections/users?sort=data.username&order=desc" \
  -H "X-API-Key: your-api-key"
```

### Pagination

```bash
# Get first 20 users
curl "https://api.cocobase.buzz/auth-collections/users?limit=20&offset=0" \
  -H "X-API-Key: your-api-key"

# Get next 20 users
curl "https://api.cocobase.buzz/auth-collections/users?limit=20&offset=20" \
  -H "X-API-Key: your-api-key"
```

### Filter Operators

All the same operators from Collections API work here:

| Operator | Example | Description |
|----------|---------|-------------|
| `eq` | `data.role=admin` | Exact match |
| `ne` | `data.status_ne=banned` | Not equal |
| `gt` | `data.age_gt=18` | Greater than |
| `gte` | `data.age_gte=18` | Greater than or equal |
| `lt` | `data.age_lt=65` | Less than |
| `lte` | `data.age_lte=65` | Less than or equal |
| `contains` | `data.username_contains=john` | Contains substring |
| `startswith` | `email_startswith=admin` | Starts with |
| `endswith` | `email_endswith=@gmail.com` | Ends with |
| `in` | `data.role_in=admin,mod` | In list |
| `notin` | `data.status_notin=banned` | Not in list |
| `isnull` | `data.bio_isnull=true` | Is null/missing |

---

## Get User by ID

Get a specific user by their ID.

**Endpoint:** `GET /auth-collections/users/{user_id}`

**Headers:**
```bash
X-API-Key: your-api-key
```

**Example:**
```bash
curl https://api.cocobase.buzz/auth-collections/users/user_abc123 \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "id": "user_abc123",
  "email": "john@example.com",
  "data": {
    "username": "johndoe",
    "full_name": "John Doe"
  },
  "created_at": "2024-01-15T10:30:00Z",
  "oauth_id": null,
  "roles": ["user"]
}
```

---

## OAuth Authentication

Authenticate users with OAuth providers (Google, Apple). Uses modern ID token verification for seamless web and mobile authentication.

**Key Features:**
- Works for both web and mobile apps
- Single API call (no redirects needed)
- Server-side token verification
- Native mobile experience
- Prevents mixed authentication

---

### Google Sign-In

Authenticate users with Google using ID token verification.

**Endpoint:** `POST /auth-collections/google-verify`

**Headers:**
```bash
X-API-Key: your-api-key
Content-Type: application/json
```

**Request Body:**
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjZmODkw...",
  "platform": "web"
}
```

**Example:**
```bash
curl -X POST https://api.cocobase.buzz/auth-collections/google-verify \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjZmODkw...",
    "platform": "web"
  }'
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@gmail.com",
    "data": {
      "username": "johndoe",
      "name": "John Doe",
      "picture": "https://lh3.googleusercontent.com/...",
      "given_name": "John",
      "family_name": "Doe"
    },
    "oauth_provider": "google",
    "created_at": "2025-11-16T10:30:00Z"
  }
}
```

**Error Responses:**
- `400` - Google Sign-In integration is not enabled
- `400` - GOOGLE_CLIENT_ID is not configured
- `400` - Invalid Google ID token
- `400` - This email is already registered with password authentication
- `400` - This email is already registered with Apple Sign-In
- `500` - An error occurred during authentication

**Configuration Required:**
- `GOOGLE_CLIENT_ID` - Your Google OAuth 2.0 Client ID (from Google Cloud Console)

**Client Implementation:**

See [google-auth-client.md](../google-auth-client.md) for complete implementation guides for:
- Web (React, Vue, vanilla JavaScript)
- React Native
- Flutter
- iOS (Swift)
- Android (Kotlin)

---

### Apple Sign-In

Authenticate users with Apple ID using ID token verification.

**Endpoint:** `POST /auth-collections/apple-verify`

**Headers:**
```bash
X-API-Key: your-api-key
Content-Type: application/json
```

**Request Body:**
```json
{
  "id_token": "eyJraWQiOiJlWGF1bm1MIiwiYWxnIjoiUlMyNTYifQ...",
  "user": {
    "name": {
      "firstName": "John",
      "lastName": "Doe"
    }
  },
  "platform": "ios"
}
```

**Notes:**
- `user` field is optional and only sent by Apple on first authentication
- Store user name immediately when received
- Subsequent logins only provide `id_token`

**Example:**
```bash
curl -X POST https://api.cocobase.buzz/auth-collections/apple-verify \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "id_token": "eyJraWQiOiJlWGF1bm1MIiwiYWxnIjoiUlMyNTYifQ...",
    "user": {
      "name": {
        "firstName": "John",
        "lastName": "Doe"
      }
    },
    "platform": "ios"
  }'
```

**Success Response (200):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@privaterelay.appleid.com",
    "data": {
      "username": "johndoe",
      "name": "John Doe",
      "is_private_email": true
    },
    "oauth_provider": "apple",
    "created_at": "2025-11-16T10:30:00Z"
  }
}
```

**Error Responses:**
- `400` - Apple Sign-In integration is not enabled
- `400` - APPLE_CLIENT_ID is not configured
- `400` - Invalid Apple ID token
- `400` - Apple ID token has expired
- `400` - This email is already registered with password authentication
- `400` - This email is already registered with Google Sign-In
- `500` - An error occurred during authentication

**Configuration Required:**
- `APPLE_CLIENT_ID` - Your Apple Service ID (web) or App Bundle ID (iOS)

**Client Implementation:**

See [apple-auth-client.md](../apple-auth-client.md) for complete implementation guides for:
- iOS (Swift, SwiftUI)
- React Native
- Web (JavaScript)

---

### OAuth Security Features

Both Google and Apple Sign-In implementations include:

- ✅ **Token Verification** - ID tokens verified using provider's public keys
- ✅ **Email Verification** - Only verified emails accepted
- ✅ **Provider Isolation** - Users can't mix authentication methods
- ✅ **Secure JWT Generation** - Your app tokens generated server-side
- ✅ **No Secrets on Client** - Client apps never handle sensitive credentials

### OAuth User Management

**First-Time Sign-In:**
- New user created automatically
- `oauth_id` set to provider's unique user ID
- `oauth_provider` set to "google" or "apple"
- Email and profile data stored

**Returning Users:**
- Logged in automatically with new JWT token
- Profile data can be updated from OAuth provider

**Mixed Authentication Prevention:**
- Users who signed up with password can't use OAuth
- Users who signed up with Google can't use Apple (and vice versa)
- Clear error messages guide users to correct authentication method

---

## User Relationships

See the [Relationships Guide](./relationships.md) for how to link users together (followers, friends, etc.) and populate those relationships in queries.

Example:
```bash
# Get users with their followers populated
curl "https://api.cocobase.buzz/auth-collections/users?populate=followers_ids" \
  -H "X-API-Key: your-api-key"
```

---

## JavaScript Examples

### Sign Up

```javascript
const response = await fetch('https://api.cocobase.buzz/auth-collections/signup', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    email: 'john@example.com',
    password: 'secure_password_123',
    data: {
      username: 'johndoe',
      age: 25
    }
  })
});

const result = await response.json();
const token = result.access_token;

// Store token for future requests
localStorage.setItem('token', token);
```

### Login

```javascript
const response = await fetch('https://api.cocobase.buzz/auth-collections/login', {
  method: 'POST',
  headers: {
    'X-API-Key': 'your-api-key',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    email: 'john@example.com',
    password: 'secure_password_123'
  })
});

const result = await response.json();
localStorage.setItem('token', result.access_token);
```

### Get Current User

```javascript
const token = localStorage.getItem('token');

const response = await fetch('https://api.cocobase.buzz/auth-collections/user', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});

const user = await response.json();
console.log(user.email); // john@example.com
```

### Update Profile

```javascript
const token = localStorage.getItem('token');

const response = await fetch('https://api.cocobase.buzz/auth-collections/user', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    data: {
      bio: 'Software developer',
      location: 'San Francisco'
    }
  })
});

const updatedUser = await response.json();
```

### Upload Profile Picture

```javascript
const token = localStorage.getItem('token');
const fileInput = document.querySelector('input[type="file"]');
const file = fileInput.files[0];

const formData = new FormData();
formData.append('profile_picture', file);
formData.append('data', JSON.stringify({
  data: { bio: 'Updated bio' }
}));

const response = await fetch('https://api.cocobase.buzz/auth-collections/user', {
  method: 'PATCH',
  headers: {
    'Authorization': `Bearer ${token}`
  },
  body: formData
});

const updatedUser = await response.json();
console.log(updatedUser.data.profile_picture); // S3 URL
```

### List Users with Filters

```javascript
const response = await fetch(
  'https://api.cocobase.buzz/auth-collections/users?data.role=admin&limit=10',
  {
    headers: {
      'X-API-Key': 'your-api-key'
    }
  }
);

const result = await response.json();
console.log(result.data); // Array of admin users
console.log(result.total); // Total count
```

---

## Python Examples

```python
import requests

API_KEY = 'your-api-key'
BASE_URL = 'https://api.cocobase.buzz'

# Sign up
response = requests.post(
    f'{BASE_URL}/auth-collections/signup',
    headers={'X-API-Key': API_KEY},
    json={
        'email': 'john@example.com',
        'password': 'secure_password_123',
        'data': {
            'username': 'johndoe',
            'age': 25
        }
    }
)
token = response.json()['access_token']

# Login
response = requests.post(
    f'{BASE_URL}/auth-collections/login',
    headers={'X-API-Key': API_KEY},
    json={
        'email': 'john@example.com',
        'password': 'secure_password_123'
    }
)
token = response.json()['access_token']

# Get current user
response = requests.get(
    f'{BASE_URL}/auth-collections/user',
    headers={'Authorization': f'Bearer {token}'}
)
user = response.json()

# Update profile
response = requests.patch(
    f'{BASE_URL}/auth-collections/user',
    headers={
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    },
    json={
        'data': {
            'bio': 'Software developer'
        }
    }
)

# List users
response = requests.get(
    f'{BASE_URL}/auth-collections/users',
    headers={'X-API-Key': API_KEY},
    params={'data.age_gte': 18, 'limit': 20}
)
result = response.json()
```

---

## Best Practices

### 1. Store Tokens Securely
```javascript
// ✅ Good: Use httpOnly cookies or secure storage
// For web apps, store in httpOnly cookies
// For mobile apps, use secure storage (Keychain/Keystore)

// ❌ Bad: Don't expose tokens in URLs or logs
```

### 2. Validate User Input
```javascript
// ✅ Good: Validate email and password on client
if (!email.includes('@')) {
  // Show error
}

// ❌ Bad: Submit invalid data and rely only on server validation
```

### 3. Handle Errors Gracefully
```javascript
// ✅ Good: Show user-friendly messages
try {
  const response = await fetch(url, options);
  if (!response.ok) {
    const error = await response.json();
    alert(`Error: ${error.detail}`);
  }
} catch (error) {
  alert('Network error. Please try again.');
}
```

### 4. Use Appropriate Filters
```bash
# ✅ Good: Specific query
?data.role=admin&data.status=active

# ❌ Bad: Fetch all and filter client-side
```

---

## Rate Limits

- **Auth requests:** 100 requests/minute per IP
- **User queries:** 500 requests/minute
- **Profile updates:** 50 requests/minute

See [Rate Limits](./rate-limits.md) for details.

---

## Next Steps

- **[Collections API](./collections.md)** - Store user-generated content
- **[Relationships](./relationships.md)** - Link users together
- **[Realtime](./realtime.md)** - Real-time user presence
- **[Storage](./storage.md)** - Upload profile pictures and files

---

**Need Help?** Contact support@cocobase.com
