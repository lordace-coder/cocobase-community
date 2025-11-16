# CocoBase Realtime & Collections Documentation

Complete guide to using CocoBase Collections and Realtime features.

**Base URL:** `https://api.cocobase.buzz`

---

## Table of Contents

1. [Collections API](#collections-api)
2. [Auth Collections](#auth-collections)
3. [Realtime Features](#realtime-features)
   - [Collection Watch (with Filters)](#1-collection-watch-with-filters)
   - [Project Broadcast](#2-project-broadcast)
   - [Room-Based Chat](#3-room-based-chat)

---

# Collections API

Store and manage JSON documents in collections (like tables in a database).

## Authentication

All requests require your project API key in the header:

```bash
X-API-Key: your-api-key-here
```

## Base Endpoint

```
GET/POST/PUT/DELETE https://api.cocobase.buzz/collections/{collection_name}/documents
```

---

## 1. Create a Document

Add a new document to a collection.

**Endpoint:** `POST /collections/{collection_name}/documents`

**Request:**
```bash
curl -X POST https://api.cocobase.buzz/collections/users/documents \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Doe",
    "email": "john@example.com",
    "age": 25,
    "status": "active"
  }'
```

**Response:**
```json
{
  "id": "doc_abc123",
  "name": "John Doe",
  "email": "john@example.com",
  "age": 25,
  "status": "active",
  "created_at": "2024-01-01T12:00:00Z"
}
```

---

## 2. Get All Documents

Retrieve all documents from a collection with optional filtering, sorting, and pagination.

**Endpoint:** `GET /collections/{collection_name}/documents`

### Basic Query
```bash
curl https://api.cocobase.buzz/collections/users/documents \
  -H "X-API-Key: your-api-key"
```

### With Filters
```bash
# Get active users over 18
curl "https://api.cocobase.buzz/collections/users/documents?status=active&age_gte=18" \
  -H "X-API-Key: your-api-key"

# Search by name (contains)
curl "https://api.cocobase.buzz/collections/users/documents?name_contains=john" \
  -H "X-API-Key: your-api-key"

# Multiple conditions
curl "https://api.cocobase.buzz/collections/users/documents?status=active&age_gte=18&age_lte=65" \
  -H "X-API-Key: your-api-key"
```

### Filter Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `field` or `field_eq` | Exact match | `status=active` |
| `field_ne` | Not equal | `status_ne=inactive` |
| `field_gt` | Greater than | `age_gt=18` |
| `field_gte` | Greater than or equal | `age_gte=18` |
| `field_lt` | Less than | `age_lt=65` |
| `field_lte` | Less than or equal | `age_lte=65` |
| `field_contains` | Contains substring (case-insensitive) | `name_contains=john` |
| `field_startswith` | Starts with | `email_startswith=admin` |
| `field_endswith` | Ends with | `email_endswith=@gmail.com` |
| `field_in` | In list (comma-separated) | `role_in=admin,moderator` |
| `field_notin` | Not in list | `status_notin=deleted,archived` |
| `field_isnull` | Is null/not null | `deleted_at_isnull=true` |

### OR Conditions
```bash
# Users who are EITHER over 65 OR have admin role
curl "https://api.cocobase.buzz/collections/users/documents?[or]age_gte=65&[or]role=admin" \
  -H "X-API-Key: your-api-key"

# Search in multiple fields (name OR email contains "john")
curl "https://api.cocobase.buzz/collections/users/documents?name__or__email_contains=john" \
  -H "X-API-Key: your-api-key"
```

### Pagination
```bash
# Get 20 documents, skip first 40
curl "https://api.cocobase.buzz/collections/users/documents?limit=20&offset=40" \
  -H "X-API-Key: your-api-key"
```

### Sorting
```bash
# Sort by age descending
curl "https://api.cocobase.buzz/collections/users/documents?sort=age&order=desc" \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "data": [
    {
      "id": "doc_abc123",
      "name": "John Doe",
      "age": 25,
      "status": "active",
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1,
  "limit": 10,
  "offset": 0,
  "has_more": false
}
```

---

## 3. Get One Document

**Endpoint:** `GET /collections/{collection_name}/documents/{document_id}`

```bash
curl https://api.cocobase.buzz/collections/users/documents/doc_abc123 \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "id": "doc_abc123",
  "name": "John Doe",
  "email": "john@example.com",
  "age": 25,
  "created_at": "2024-01-01T12:00:00Z"
}
```

---

## 4. Update a Document

**Endpoint:** `PUT /collections/{collection_name}/documents/{document_id}`

```bash
curl -X PUT https://api.cocobase.buzz/collections/users/documents/doc_abc123 \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "age": 26,
    "status": "premium"
  }'
```

**Response:** Returns the updated document.

---

## 5. Delete a Document

**Endpoint:** `DELETE /collections/{collection_name}/documents/{document_id}`

```bash
curl -X DELETE https://api.cocobase.buzz/collections/users/documents/doc_abc123 \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "status": "success",
  "message": "Document deleted successfully"
}
```

---

## 6. Batch Operations

### Batch Create
```bash
curl -X POST https://api.cocobase.buzz/collections/users/batch/documents \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {"name": "Alice", "age": 30},
      {"name": "Bob", "age": 25},
      {"name": "Charlie", "age": 35}
    ]
  }'
```

### Batch Update
```bash
curl -X POST https://api.cocobase.buzz/collections/users/batch/documents/update \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "updates": {
      "doc_abc123": {"data": {"status": "premium"}},
      "doc_xyz789": {"data": {"status": "active"}}
    }
  }'
```

### Batch Delete
```bash
curl -X POST https://api.cocobase.buzz/collections/users/batch/documents/delete \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "document_ids": ["doc_abc123", "doc_xyz789"]
  }'
```

---

# Auth Collections

Special collections for user authentication with built-in password hashing and role management.

## Base Endpoint

```
POST/GET https://api.cocobase.buzz/auth-collections/{collection_name}/...
```

---

## 1. Register a User

**Endpoint:** `POST /auth-collections/{collection_name}/register`

```bash
curl -X POST https://api.cocobase.buzz/auth-collections/users/register \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123!",
    "name": "John Doe",
    "age": 25
  }'
```

**Response:**
```json
{
  "id": "user_abc123",
  "email": "john@example.com",
  "name": "John Doe",
  "age": 25,
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Note:** Password is automatically hashed and never returned in responses.

---

## 2. Login

**Endpoint:** `POST /auth-collections/{collection_name}/login`

```bash
curl -X POST https://api.cocobase.buzz/auth-collections/users/login \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": "user_abc123",
    "email": "john@example.com",
    "name": "John Doe"
  }
}
```

---

## 3. Get Current User

**Endpoint:** `GET /auth-collections/{collection_name}/me`

```bash
curl https://api.cocobase.buzz/auth-collections/users/me \
  -H "X-API-Key: your-api-key" \
  -H "Authorization: Bearer your-jwt-token"
```

**Response:**
```json
{
  "id": "user_abc123",
  "email": "john@example.com",
  "name": "John Doe",
  "roles": ["user"]
}
```

---

## 4. Update User

**Endpoint:** `PUT /auth-collections/{collection_name}/me`

```bash
curl -X PUT https://api.cocobase.buzz/auth-collections/users/me \
  -H "X-API-Key: your-api-key" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "John Smith",
    "age": 26
  }'
```

---

## 5. Change Password

**Endpoint:** `POST /auth-collections/{collection_name}/change-password`

```bash
curl -X POST https://api.cocobase.buzz/auth-collections/users/change-password \
  -H "X-API-Key: your-api-key" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "old_password": "SecurePass123!",
    "new_password": "NewSecurePass456!"
  }'
```

---

# Realtime Features

CocoBase provides 3 types of WebSocket connections for real-time updates.

## WebSocket Base URL

```
wss://api.cocobase.buzz/realtime/...
```

---

## 1. Collection Watch (with Filters)

Watch for changes to documents in a collection with optional filtering.

### Endpoint
```
wss://api.cocobase.buzz/realtime/collections/{collection_name}
```

### JavaScript Example

```javascript
// Connect to collection
const ws = new WebSocket('wss://api.cocobase.buzz/realtime/collections/users');

ws.onopen = () => {
  console.log('Connected to collection watch');

  // STEP 1: Authenticate with optional filters
  ws.send(JSON.stringify({
    api_key: "your-api-key",
    filters: {
      "status": "active",        // Only watch active users
      "age_gte": "18",           // Age >= 18
      "role_in": "admin,mod"     // Only admins and moderators
    }
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  // STEP 2: Connection confirmation
  if (message.event === "connected") {
    console.log(`Connected to collection: ${message.collection_id}`);
    console.log(`Active filters:`, message.filters);
  }

  // STEP 3: Receive filtered document events
  if (message.event === "create") {
    console.log('New document created:', message.data);
  }

  if (message.event === "update") {
    console.log('Document updated:', message.data);
    console.log('Old data:', message.old_data);
  }

  if (message.event === "delete") {
    console.log('Document deleted:', message.data);
  }
};

ws.onclose = () => {
  console.log('Disconnected from collection watch');
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};
```

### Without Filters (Watch All Changes)

```javascript
ws.send(JSON.stringify({
  api_key: "your-api-key"
  // No filters = receive all events
}));
```

### Message Format

**Server → Client (Events):**
```json
{
  "event": "create|update|delete",
  "collection_id": "users",
  "data": {
    "id": "doc_abc123",
    "name": "John Doe",
    "age": 25,
    "status": "active"
  },
  "old_data": {
    // Only for "update" events
    "age": 24
  }
}
```

### Use Cases
- Live dashboards showing filtered data
- Real-time notifications for specific events
- Collaborative editing with filtered views
- Activity feeds with user-specific filters

---

## 2. Project Broadcast

Global messaging system where all clients in your project can send and receive messages.

### Endpoint
```
wss://api.cocobase.buzz/realtime/broadcast
```

### JavaScript Example

```javascript
const ws = new WebSocket('wss://api.cocobase.buzz/realtime/broadcast');

ws.onopen = () => {
  console.log('Connected to project broadcast');

  // STEP 1: Authenticate with user info
  ws.send(JSON.stringify({
    api_key: "your-api-key",
    user_id: "user_123",        // Optional: Your user ID
    user_name: "John Doe"       // Optional: Display name
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  // STEP 2: Connection confirmation
  if (message.event === "connected") {
    console.log(`Connected to project: ${message.project_id}`);
    console.log(`Your user ID: ${message.user_id}`);

    // STEP 3: Send a broadcast message
    ws.send(JSON.stringify({
      type: "message",
      data: {
        text: "Hello everyone!",
        priority: "high",
        action: "new_sale"
      }
    }));
  }

  // STEP 4: Receive broadcasts from all clients
  if (message.type === "message") {
    console.log(`${message.user_name} (${message.user_id}):`);
    console.log('Data:', message.data);
    console.log('Sent at:', message.timestamp);
  }
};

// Ping/Pong for keeping connection alive
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "ping" }));
  }
}, 30000); // Every 30 seconds
```

### Message Formats

**Client → Server (Send broadcast):**
```json
{
  "type": "message",
  "data": {
    "text": "Server is going down for maintenance",
    "level": "warning",
    "timestamp": "2024-01-01T15:00:00Z"
  }
}
```

**Server → All Clients (Broadcast):**
```json
{
  "type": "message",
  "user_id": "user_123",
  "user_name": "John Doe",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "text": "Server is going down for maintenance",
    "level": "warning",
    "timestamp": "2024-01-01T15:00:00Z"
  }
}
```

### Use Cases
- System-wide notifications
- Global announcements
- Team collaboration updates
- Real-time dashboard syncing across all users
- Activity broadcasting

---

## 3. Room-Based Chat

Create or join topic-specific rooms for group messaging.

### Endpoint
```
wss://api.cocobase.buzz/realtime/rooms/{room_id}
```

### JavaScript Example - Create Room

```javascript
const roomId = "general-chat";
const ws = new WebSocket(`wss://api.cocobase.buzz/realtime/rooms/${roomId}`);

ws.onopen = () => {
  console.log('Connected to room socket');

  // STEP 1: Authenticate and CREATE room
  ws.send(JSON.stringify({
    api_key: "your-api-key",
    user_id: "user_123",
    user_name: "John Doe",
    action: "create",              // Create new room
    room_title: "General Chat"     // Room display name
  }));
};

ws.onmessage = (event) => {
  const message = JSON.parse(event.data);

  // STEP 2: Room joined confirmation
  if (message.event === "joined") {
    console.log(`Joined room: ${message.room_title}`);
    console.log(`Room ID: ${message.room_id}`);
    console.log(`Participants: ${message.participants}`);

    // STEP 3: Send a message to the room
    ws.send(JSON.stringify({
      type: "message",
      content: "Hello everyone in this room!"
    }));
  }

  // STEP 4: Receive messages
  if (message.type === "message") {
    console.log(`${message.user_name}: ${message.content}`);
    console.log('Room:', message.room_info.title);
    console.log('Sent at:', message.timestamp);
  }

  // User joined notification
  if (message.type === "user_joined") {
    console.log(`${message.user_name} joined the room`);
    console.log(`Now ${message.room_info.participants} participants`);
  }

  // User left notification
  if (message.type === "user_left") {
    console.log(`${message.user_name} left the room`);
    console.log(`Now ${message.room_info.participants} participants`);
  }
};
```

### Join Existing Room

```javascript
ws.send(JSON.stringify({
  api_key: "your-api-key",
  user_id: "user_456",
  user_name: "Jane Smith",
  action: "join"  // Join existing room (will fail if room doesn't exist)
}));
```

### List All Rooms (REST API)

```bash
curl https://api.cocobase.buzz/realtime/rooms \
  -H "X-API-Key: your-api-key"
```

**Response:**
```json
{
  "rooms": [
    {
      "id": "general-chat",
      "title": "General Chat",
      "created_by": "user_123",
      "participants": 5,
      "participant_list": [
        {"id": "user_123", "name": "John Doe"},
        {"id": "user_456", "name": "Jane Smith"}
      ],
      "created_at": 1704110400.0
    }
  ],
  "total": 1
}
```

### Message Formats

**Client → Server (Send message):**
```json
{
  "type": "message",
  "content": "Hello everyone!"
}
```

**Server → Room Participants:**

**1. Message Event:**
```json
{
  "type": "message",
  "user_id": "user_123",
  "user_name": "John Doe",
  "content": "Hello everyone!",
  "timestamp": "2024-01-01T12:00:00Z",
  "room_info": {
    "id": "general-chat",
    "title": "General Chat",
    "participants": 5
  }
}
```

**2. User Joined Event:**
```json
{
  "type": "user_joined",
  "user_id": "user_789",
  "user_name": "Bob Wilson",
  "timestamp": "2024-01-01T12:05:00Z",
  "room_info": {
    "id": "general-chat",
    "title": "General Chat",
    "participants": 6
  }
}
```

**3. User Left Event:**
```json
{
  "type": "user_left",
  "user_id": "user_456",
  "user_name": "Jane Smith",
  "timestamp": "2024-01-01T12:10:00Z",
  "room_info": {
    "id": "general-chat",
    "title": "General Chat",
    "participants": 5
  }
}
```

### Use Cases
- Chat rooms
- Topic-specific discussions
- Team channels
- Support ticket rooms
- Event-based messaging
- Private group conversations

---

## React/Vue Example - Collection Watch

```javascript
import { useEffect, useState } from 'react';

function useCollectionWatch(collectionName, filters = {}) {
  const [data, setData] = useState([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(
      `wss://api.cocobase.buzz/realtime/collections/${collectionName}`
    );

    ws.onopen = () => {
      ws.send(JSON.stringify({
        api_key: process.env.REACT_APP_API_KEY,
        filters: filters
      }));
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      if (message.event === "connected") {
        setConnected(true);
      }

      if (message.event === "create") {
        setData(prev => [...prev, message.data]);
      }

      if (message.event === "update") {
        setData(prev => prev.map(item =>
          item.id === message.data.id ? message.data : item
        ));
      }

      if (message.event === "delete") {
        setData(prev => prev.filter(item => item.id !== message.data.id));
      }
    };

    return () => ws.close();
  }, [collectionName, filters]);

  return { data, connected };
}

// Usage
function ActiveUsers() {
  const { data: activeUsers, connected } = useCollectionWatch('users', {
    status: 'active',
    age_gte: '18'
  });

  return (
    <div>
      <p>Status: {connected ? 'Connected' : 'Connecting...'}</p>
      <h2>Active Users ({activeUsers.length})</h2>
      {activeUsers.map(user => (
        <div key={user.id}>
          {user.name} - {user.email}
        </div>
      ))}
    </div>
  );
}
```

---

## Error Handling

All WebSocket connections return errors in this format:

```json
{
  "error": "Authentication failed",
  "error_detail": "Invalid API key"
}
```

Common errors:
- `"API key is required"` - Missing api_key in auth message
- `"Invalid API key"` - Wrong API key or project not found
- `"Collection not found or access denied"` - Collection doesn't exist or wrong project
- `"Room not found"` - Trying to join non-existent room
- `"Authentication timeout"` - Didn't send auth message within 10 seconds

---

## Best Practices

### 1. Keep Connections Alive
```javascript
// Send ping every 30 seconds
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ type: "ping" }));
  }
}, 30000);
```

### 2. Reconnect on Disconnect
```javascript
let ws;
let reconnectAttempts = 0;
const maxReconnectAttempts = 5;

function connect() {
  ws = new WebSocket('wss://api.cocobase.buzz/realtime/broadcast');

  ws.onclose = () => {
    if (reconnectAttempts < maxReconnectAttempts) {
      reconnectAttempts++;
      setTimeout(connect, 1000 * reconnectAttempts); // Exponential backoff
    }
  };

  ws.onopen = () => {
    reconnectAttempts = 0; // Reset on successful connection
  };
}
```

### 3. Use Filters Efficiently
```javascript
// ✅ Good: Filter on server
const ws = new WebSocket('wss://api.cocobase.buzz/realtime/collections/orders');
ws.send(JSON.stringify({
  api_key: "your-api-key",
  filters: {
    status: "pending",
    total_gte: "100"
  }
}));

// ❌ Bad: Receive all and filter on client
// This wastes bandwidth and processing
```

### 4. Clean Up Connections
```javascript
// React example
useEffect(() => {
  const ws = new WebSocket('...');

  // ... setup

  return () => {
    ws.close(); // Clean up when component unmounts
  };
}, []);
```

---

## Rate Limits

- **Collections API:** 1000 requests per minute
- **WebSocket Connections:** 100 concurrent connections per project
- **Messages:** No limit on messages per connection

---

## Support

For issues or questions:
- Email: support@cocobase.com
- Documentation: https://cocobase.buzz/docs
- GitHub: https://github.com/cocobase/issues

---

**Happy Building! 🚀**
