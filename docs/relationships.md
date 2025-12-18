# Relationships Guide

Link documents and users together to create relational data structures.

**Applies to:** Collections API, Auth Collections API

---

## Table of Contents

1. [Overview](#overview)
2. [Relationship Types](#relationship-types)
3. [Creating Relationships](#creating-relationships)
4. [Populating Relationships](#populating-relationships)
5. [Social Features](#social-features)
6. [Best Practices](#best-practices)
7. [Complete Examples](#complete-examples)

---

## Overview

CocoBase supports relationships between:

- **User → User** (followers, friends, referred_by)
- **User → Document** (favorite posts, bookmarks)
- **Document → Document** (comments on posts, product reviews)

Relationships are stored as **ID references** in your data and can be **populated** on demand.

---

## Relationship Types

### One-to-One

A single reference to another entity:

```json
{
  "id": "user_123",
  "email": "john@example.com",
  "data": {
    "username": "johndoe",
    "referred_by": "user_456"
  }
}
```

### One-to-Many / Many-to-Many

An array of references:

```json
{
  "id": "user_123",
  "email": "john@example.com",
  "data": {
    "username": "johndoe",
    "followers_ids": ["user_456", "user_789", "user_012"],
    "following_ids": ["user_456", "user_999"]
  }
}
```

---

## Creating Relationships

### User to User Relationships

**Example: Referral System**

```bash
# User 1 signs up (no referrer)
curl -X POST https://api.cocobase.buzz/auth-collections/signup \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "password123",
    "data": {
      "username": "alice"
    }
  }'

# Response: { "access_token": "..." }
# User ID: user_abc123

# User 2 signs up with referral
curl -X POST https://api.cocobase.buzz/auth-collections/signup \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "bob@example.com",
    "password": "password123",
    "data": {
      "username": "bob",
      "referred_by": "user_abc123"
    }
  }'
```

**Example: Follow System**

```bash
# User follows another user
curl -X PATCH https://api.cocobase.buzz/auth-collections/user \
  -H "Authorization: Bearer user-token" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "following_ids": ["user_456", "user_789"]
    }
  }'
```

**JavaScript:**

```javascript
// Follow a user
const currentUser = await getCurrentUser(); // Assume this gets current user

const currentFollowing = currentUser.data.following_ids || [];
const newFollowing = [...currentFollowing, "user_to_follow"];

await fetch("https://api.cocobase.buzz/auth-collections/user", {
  method: "PATCH",
  headers: {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    data: {
      following_ids: newFollowing,
    },
  }),
});

// Unfollow a user
const updatedFollowing = currentFollowing.filter(
  (id) => id !== "user_to_unfollow"
);

await fetch("https://api.cocobase.buzz/auth-collections/user", {
  method: "PATCH",
  headers: {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    data: {
      following_ids: updatedFollowing,
    },
  }),
});
```

### User to Document Relationships

**Example: User Favorites**

```bash
# User bookmarks posts
curl -X PATCH https://api.cocobase.buzz/auth-collections/user \
  -H "Authorization: Bearer user-token" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "bookmarked_posts": ["doc_post123", "doc_post456"]
    }
  }'
```

### Document to Document Relationships

**Example: Comments on Posts**

```bash
# Create a post
curl -X POST https://api.cocobase.buzz/collections/posts/documents \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My first post",
    "content": "Hello world!",
    "author_id": "user_123"
  }'

# Response: { "id": "doc_post123", ... }

# Create a comment
curl -X POST https://api.cocobase.buzz/collections/comments/documents \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "post_id": "doc_post123",
    "author_id": "user_456",
    "text": "Great post!"
  }'
```

---

## Populating Relationships

Instead of just getting IDs, you can **populate** relationships to get the full related data.

### Basic Population

**Without Population:**

```json
{
  "id": "user_123",
  "email": "john@example.com",
  "data": {
    "username": "johndoe",
    "referred_by": "user_456"
  }
}
```

**With Population:**

```bash
curl "https://api.cocobase.buzz/auth-collections/users?populate=referred_by" \
  -H "X-API-Key: your-api-key"
```

### Explicit Source Specification (NEW!)

By default, CocoBase auto-detects whether to fetch from AppUser or a collection by pluralizing the field name. You can override this behavior to explicitly specify the source.

**Syntax:** `populate=field:source`

#### Force AppUser Model

```bash
# Force fetch from AppUser model (not from a collection)
curl "https://api.cocobase.buzz/collections/posts/documents?populate=author:appuser" \
  -H "X-API-Key: your-api-key"
```

Use this when:

- You have a collection named "users" that conflicts with AppUser
- You want to ensure it fetches from the system users table
- You need guaranteed AppUser data (email, created_at, roles)

#### Force Specific Collection

```bash
# Force fetch from "members" collection instead of pluralizing to "users"
curl "https://api.cocobase.buzz/collections/teams/documents?populate=user:members" \
  -H "X-API-Key: your-api-key"

# Force fetch from "posts" collection
curl "https://api.cocobase.buzz/collections/comments/documents?populate=author:posts" \
  -H "X-API-Key: your-api-key"
```

Use this when:

- Your collection name doesn't follow standard pluralization
- You want to avoid relying on auto-pluralization
- You have custom naming conventions

**Examples:**

```bash
# Auto-detect (default) - pluralizes "author" to "authors" collection
GET /collections/posts/documents?populate=author

# Force AppUser
GET /collections/posts/documents?populate=author:appuser

# Force specific collection "team_members"
GET /collections/projects/documents?populate=owner:team_members
```

**JavaScript:**

```javascript
// Auto-detect
const params = new URLSearchParams({
  populate: "author",
});

// Force AppUser
const params = new URLSearchParams({
  populate: "author:appuser",
});

// Force specific collection
const params = new URLSearchParams({
  populate: "owner:team_members",
});

const response = await fetch(
  `https://api.cocobase.buzz/collections/posts/documents?${params}`,
  {
    headers: { "X-API-Key": "your-api-key" },
  }
);
```

**Response:**

```json
{
  "data": [
    {
      "id": "user_123",
      "email": "john@example.com",
      "data": {
        "username": "johndoe",
        "referred_by": "user_456",
        "referred_by": {
          "id": "user_456",
          "email": "alice@example.com",
          "data": {
            "username": "alice"
          },
          "created_at": "2024-01-10T10:00:00Z"
        }
      },
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Populate Multiple Fields

```bash
curl "https://api.cocobase.buzz/auth-collections/users?populate=referred_by&populate=followers_ids" \
  -H "X-API-Key: your-api-key"
```

**JavaScript:**

```javascript
const params = new URLSearchParams({
  populate: ["referred_by", "followers_ids"],
});

const response = await fetch(
  `https://api.cocobase.buzz/auth-collections/users?${params}`,
  {
    headers: { "X-API-Key": "your-api-key" },
  }
);

const result = await response.json();
```

**Response:**

```json
{
  "data": [
    {
      "id": "user_123",
      "email": "john@example.com",
      "data": {
        "username": "johndoe",
        "referred_by": "user_456",
        "referred_by": {
          "id": "user_456",
          "email": "alice@example.com",
          "data": { "username": "alice" }
        },
        "followers_ids": ["user_789", "user_012"],
        "followers_ids": [
          {
            "id": "user_789",
            "email": "bob@example.com",
            "data": { "username": "bob" }
          },
          {
            "id": "user_012",
            "email": "charlie@example.com",
            "data": { "username": "charlie" }
          }
        ]
      }
    }
  ]
}
```

### Populate Arrays

For array relationships (one-to-many, many-to-many):

```bash
# Get users with their followers populated
curl "https://api.cocobase.buzz/auth-collections/users?populate=followers_ids" \
  -H "X-API-Key: your-api-key"
```

**Response:**

```json
{
  "data": [
    {
      "id": "user_123",
      "data": {
        "followers_ids": ["user_456", "user_789"],
        "followers_ids": [
          {
            "id": "user_456",
            "email": "alice@example.com",
            "data": { "username": "alice" }
          },
          {
            "id": "user_789",
            "email": "bob@example.com",
            "data": { "username": "bob" }
          }
        ]
      }
    }
  ]
}
```

---

## Social Features

### Follow System

**Data Structure:**

```json
{
  "id": "user_123",
  "email": "john@example.com",
  "data": {
    "username": "johndoe",
    "followers_ids": ["user_456", "user_789"],
    "following_ids": ["user_456", "user_999"]
  }
}
```

**Get User's Followers:**

```bash
curl "https://api.cocobase.buzz/auth-collections/users/user_123?populate=followers_ids" \
  -H "X-API-Key: your-api-key"
```

**Get User's Following:**

```bash
curl "https://api.cocobase.buzz/auth-collections/users/user_123?populate=following_ids" \
  -H "X-API-Key: your-api-key"
```

**Find Who Follows a User:**

```bash
# Find all users who have "user_123" in their following list
curl "https://api.cocobase.buzz/auth-collections/users?data.following_ids_array_contains=user_123" \
  -H "X-API-Key: your-api-key"
```

**JavaScript Follow/Unfollow:**

```javascript
class FollowSystem {
  constructor(apiKey, token) {
    this.apiKey = apiKey;
    this.token = token;
  }

  async getCurrentUser() {
    const response = await fetch(
      "https://api.cocobase.buzz/auth-collections/user",
      {
        headers: {
          Authorization: `Bearer ${this.token}`,
        },
      }
    );
    return await response.json();
  }

  async follow(userIdToFollow) {
    const currentUser = await this.getCurrentUser();
    const following = currentUser.data.following_ids || [];

    if (following.includes(userIdToFollow)) {
      console.log("Already following");
      return;
    }

    await fetch("https://api.cocobase.buzz/auth-collections/user", {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        data: {
          following_ids: [...following, userIdToFollow],
        },
      }),
    });
  }

  async unfollow(userIdToUnfollow) {
    const currentUser = await this.getCurrentUser();
    const following = currentUser.data.following_ids || [];

    await fetch("https://api.cocobase.buzz/auth-collections/user", {
      method: "PATCH",
      headers: {
        Authorization: `Bearer ${this.token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        data: {
          following_ids: following.filter((id) => id !== userIdToUnfollow),
        },
      }),
    });
  }

  async getFollowers(userId) {
    const response = await fetch(
      `https://api.cocobase.buzz/auth-collections/users/${userId}?populate=followers_ids`,
      {
        headers: {
          "X-API-Key": this.apiKey,
        },
      }
    );
    const user = await response.json();
    return user.data.followers_ids || [];
  }

  async getFollowing(userId) {
    const response = await fetch(
      `https://api.cocobase.buzz/auth-collections/users/${userId}?populate=following_ids`,
      {
        headers: {
          "X-API-Key": this.apiKey,
        },
      }
    );
    const user = await response.json();
    return user.data.following_ids || [];
  }
}

// Usage
const followSystem = new FollowSystem("your-api-key", userToken);

// Follow a user
await followSystem.follow("user_456");

// Get followers
const followers = await followSystem.getFollowers("user_123");
console.log("Followers:", followers);
```

### Referral System

**Data Structure:**

```json
{
  "id": "user_123",
  "email": "john@example.com",
  "data": {
    "username": "johndoe",
    "referred_by": "user_456"
  }
}
```

**Sign Up with Referral:**

```bash
curl -X POST https://api.cocobase.buzz/auth-collections/signup \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "newuser@example.com",
    "password": "password123",
    "data": {
      "username": "newuser",
      "referred_by": "user_456"
    }
  }'
```

**Get User Who Referred Me:**

```bash
curl "https://api.cocobase.buzz/auth-collections/user?populate=referred_by" \
  -H "Authorization: Bearer user-token"
```

**Get All Users I Referred:**

```bash
curl "https://api.cocobase.buzz/auth-collections/users?data.referred_by=user_123" \
  -H "X-API-Key: your-api-key"
```

**JavaScript:**

```javascript
async function getReferralStats(apiKey, userId) {
  // Get the user who referred this user
  const userResponse = await fetch(
    `https://api.cocobase.buzz/auth-collections/users/${userId}?populate=referred_by`,
    {
      headers: { "X-API-Key": apiKey },
    }
  );
  const user = await userResponse.json();

  // Get all users this user referred
  const referralsResponse = await fetch(
    `https://api.cocobase.buzz/auth-collections/users?data.referred_by=${userId}`,
    {
      headers: { "X-API-Key": apiKey },
    }
  );
  const referrals = await referralsResponse.json();

  return {
    referredBy: user.data.referred_by,
    referralCount: referrals.total,
    referrals: referrals.data,
  };
}

// Usage
const stats = await getReferralStats("your-api-key", "user_123");
console.log("Referred by:", stats.referredBy?.data?.username);
console.log("Total referrals:", stats.referralCount);
```

### Friends System

**Data Structure:**

```json
{
  "id": "user_123",
  "email": "john@example.com",
  "data": {
    "username": "johndoe",
    "friend_ids": ["user_456", "user_789"],
    "pending_friend_requests": ["user_999"]
  }
}
```

**Send Friend Request:**

```javascript
async function sendFriendRequest(token, targetUserId) {
  // Add to current user's pending requests
  const currentUser = await getCurrentUser(token);
  const pending = currentUser.data.pending_friend_requests || [];

  await fetch("https://api.cocobase.buzz/auth-collections/user", {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      data: {
        pending_friend_requests: [...pending, targetUserId],
      },
    }),
  });
}

async function acceptFriendRequest(token, requesterId) {
  const currentUser = await getCurrentUser(token);

  // Remove from pending
  const pending = currentUser.data.pending_friend_requests || [];
  const updatedPending = pending.filter((id) => id !== requesterId);

  // Add to friends
  const friends = currentUser.data.friend_ids || [];

  await fetch("https://api.cocobase.buzz/auth-collections/user", {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      data: {
        friend_ids: [...friends, requesterId],
        pending_friend_requests: updatedPending,
      },
    }),
  });
}
```

---

## Best Practices

### 1. Use Batch Queries

The populate feature uses **optimized batch queries** to avoid N+1 problems:

```bash
# ✅ Good: Single query with populate
?populate=followers_ids&populate=following_ids

# ❌ Bad: Multiple queries for each relationship
# This creates N+1 queries and is very slow
```

### 2. Don't Over-Populate

Only populate what you need:

```bash
# ✅ Good: Only populate what's needed for this view
?populate=referred_by

# ❌ Bad: Populating unnecessary relationships
?populate=followers_ids&populate=following_ids&populate=referred_by
# (when you only need referred_by)
```

### 3. Use Array Contains for Reverse Lookups

Finding "who follows me" efficiently:

```bash
# ✅ Good: Use array_contains
?data.following_ids_array_contains=user_123

# ❌ Bad: Fetch all users and filter client-side
```

### 4. Keep Relationship Arrays Reasonable

Don't store thousands of IDs in a single array:

```bash
# ✅ Good: Reasonable array size (< 1000 items)
"followers_ids": ["user_1", "user_2", ..., "user_500"]

# ❌ Bad: Massive arrays (> 10,000 items)
# Consider pagination or a separate collection for this
```

### 5. Use Filters with Population

Combine filters and population for powerful queries:

```bash
# Get active users with their referrers
curl "https://api.cocobase.buzz/auth-collections/users?status=active&populate=referred_by" \
  -H "X-API-Key: your-api-key"
```

### 6. Cache Populated Results

Cache frequently accessed relationships:

```javascript
const cache = new Map();

async function getUserWithRelationships(userId, populate) {
  const cacheKey = `${userId}:${populate.join(",")}`;

  if (cache.has(cacheKey)) {
    return cache.get(cacheKey);
  }

  const params = new URLSearchParams();
  populate.forEach((field) => params.append("populate", field));

  const response = await fetch(
    `https://api.cocobase.buzz/auth-collections/users/${userId}?${params}`,
    {
      headers: { "X-API-Key": "your-api-key" },
    }
  );

  const data = await response.json();
  cache.set(cacheKey, data);

  return data;
}
```

---

## Complete Examples

### Social Network Profile

```javascript
async function getSocialProfile(apiKey, userId) {
  const params = new URLSearchParams({
    populate: ["followers_ids", "following_ids", "friend_ids"],
  });

  const response = await fetch(
    `https://api.cocobase.buzz/auth-collections/users/${userId}?${params}`,
    {
      headers: { "X-API-Key": apiKey },
    }
  );

  const user = await response.json();

  return {
    user: {
      id: user.id,
      username: user.data.username,
      email: user.email,
    },
    followers: user.data.followers_ids || [],
    following: user.data.following_ids || [],
    friends: user.data.friend_ids || [],
    stats: {
      followersCount: (user.data.followers_ids || []).length,
      followingCount: (user.data.following_ids || []).length,
      friendsCount: (user.data.friend_ids || []).length,
    },
  };
}

// Usage
const profile = await getSocialProfile("your-api-key", "user_123");
console.log("Followers:", profile.followers);
console.log("Stats:", profile.stats);
```

### Blog with Comments

```javascript
async function getPostWithComments(apiKey, postId) {
  // Get the post
  const postResponse = await fetch(
    `https://api.cocobase.buzz/collections/posts/documents/${postId}`,
    {
      headers: { "X-API-Key": apiKey },
    }
  );
  const post = await postResponse.json();

  // Get all comments for this post
  const commentsResponse = await fetch(
    `https://api.cocobase.buzz/collections/comments/documents?post_id=${postId}`,
    {
      headers: { "X-API-Key": apiKey },
    }
  );
  const comments = await commentsResponse.json();

  return {
    post,
    comments: comments.data,
    commentCount: comments.total,
  };
}
```

### E-commerce with Reviews

```javascript
async function getProductWithReviews(apiKey, productId) {
  // Get product
  const productResponse = await fetch(
    `https://api.cocobase.buzz/collections/products/documents/${productId}`,
    {
      headers: { "X-API-Key": apiKey },
    }
  );
  const product = await productResponse.json();

  // Get reviews
  const reviewsResponse = await fetch(
    `https://api.cocobase.buzz/collections/reviews/documents?product_id=${productId}&sort=created_at&order=desc&limit=10`,
    {
      headers: { "X-API-Key": apiKey },
    }
  );
  const reviews = await reviewsResponse.json();

  // Calculate average rating
  const avgRating =
    reviews.data.reduce((sum, r) => sum + r.rating, 0) / reviews.total;

  return {
    product,
    reviews: reviews.data,
    stats: {
      totalReviews: reviews.total,
      averageRating: avgRating.toFixed(1),
    },
  };
}
```

---

## Next Steps

- **[Collections API](./collections.md)** - Full collections documentation
- **[Auth Collections](./auth-collections.md)** - User authentication
- **[Filtering Guide](./filtering.md)** - Advanced filtering techniques
- **[Realtime](./realtime.md)** - Real-time updates

---

**Need Help?** Contact support@cocobase.com
