# Cocobase OAuth Client API Integration Guide

This guide explains how to integrate with the Cocobase OAuth API to allow your users to create and manage OAuth clients for their applications.

## Overview

Your Next.js dashboard needs to call Cocobase OAuth API endpoints to enable users to:
1. Create OAuth clients for their third-party applications
2. List all their existing OAuth clients
3. Update OAuth client settings (redirect URIs, scopes)
4. Delete OAuth clients

## Authentication

All Cocobase API calls require authentication using a Bearer token in the `Authorization` header.

```typescript
// Get the authentication token (stored after user logs in)
const authToken = localStorage.getItem('cocobase_auth_token');

// Include in all API calls
headers: {
  'Authorization': `Bearer ${authToken}`,
  'Content-Type': 'application/json'
}
```

---

## API Endpoints Reference

All OAuth endpoints are under `/oauth/` and require authentication via `Authorization: Bearer <token>` header.

### 1. List All OAuth Clients

```bash
GET /oauth/clients
Authorization: Bearer <your_auth_token>
```

**Response**:
```json
{
  "clients": [
    {
      "id": "uuid-1234",
      "client_id": "client_abc123",
      "name": "My Mobile App",
      "description": "OAuth client for mobile application",
      "redirect_uris": ["https://myapp.com/callback", "http://localhost:3000/callback"],
      "scopes": ["openid", "email", "profile"],
      "is_confidential": true,
      "created_at": "2025-01-10T12:00:00",
      "updated_at": "2025-01-10T12:00:00"
    }
  ]
}
```

**How to call from Next.js**:
```typescript
const response = await fetch('https://your-cocobase-api.com/oauth/clients', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${authToken}`,
    'Content-Type': 'application/json'
  }
});

const data = await response.json();
const clients = data.clients;
```

---

### 2. Get Single OAuth Client

```bash
GET /oauth/clients/{client_id}
Authorization: Bearer <your_auth_token>
```

**Response**:
```json
{
  "id": "uuid-1234",
  "client_id": "client_abc123",
  "name": "My Mobile App",
  "description": "OAuth client for mobile application",
  "redirect_uris": ["https://myapp.com/callback"],
  "scopes": ["openid", "email", "profile"],
  "is_confidential": true,
  "created_at": "2025-01-10T12:00:00",
  "updated_at": "2025-01-10T12:00:00"
}
```

**How to call from Next.js**:
```typescript
const response = await fetch(`https://your-cocobase-api.com/oauth/clients/${clientId}`, {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${authToken}`,
    'Content-Type': 'application/json'
  }
});

const client = await response.json();
```

---

### 3. Create OAuth Client

```bash
POST /oauth/clients
Authorization: Bearer <your_auth_token>
Content-Type: application/json

{
  "name": "My Mobile App",
  "description": "OAuth client for my mobile application",
  "redirect_uris": ["https://myapp.com/callback", "http://localhost:3000/callback"],
  "scopes": ["openid", "email", "profile"],
  "is_confidential": true
}
```

**Response** (client_secret is ONLY shown once!):
```json
{
  "id": "uuid-1234",
  "client_id": "client_abc123",
  "client_secret": "secret_xyz789_SAVE_THIS_NOW",
  "name": "My Mobile App",
  "description": "OAuth client for my mobile application",
  "redirect_uris": ["https://myapp.com/callback"],
  "scopes": ["openid", "email", "profile"],
  "is_confidential": true,
  "created_at": "2025-01-10T12:00:00"
}
```

**How to call from Next.js**:
```typescript
const response = await fetch('https://your-cocobase-api.com/oauth/clients', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${authToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: formData.name,
    description: formData.description,
    redirect_uris: formData.redirect_uris.split(',').map(uri => uri.trim()),
    scopes: formData.scopes.split(',').map(s => s.trim()),
    is_confidential: true
  })
});

const data = await response.json();

if (response.ok) {
  // CRITICAL: Save client_secret immediately - it's only shown once!
  console.log('Client ID:', data.client_id);
  console.log('Client Secret:', data.client_secret); // Save this!

  // Show to user with copy button
  setClientSecret(data.client_secret);
}
```

---

### 4. Update OAuth Client

```bash
PUT /oauth/clients/{client_id}
Authorization: Bearer <your_auth_token>
Content-Type: application/json

{
  "name": "Updated App Name",
  "description": "Updated description",
  "redirect_uris": ["https://newdomain.com/callback"],
  "scopes": ["openid", "email", "profile"]
}
```

**Note**: All fields are optional. Only send the fields you want to update.

**Response**:
```json
{
  "id": "uuid-1234",
  "client_id": "client_abc123",
  "name": "Updated App Name",
  "description": "Updated description",
  "redirect_uris": ["https://newdomain.com/callback"],
  "scopes": ["openid", "email", "profile"],
  "is_confidential": true,
  "created_at": "2025-01-10T12:00:00",
  "updated_at": "2025-01-11T14:30:00",
  "message": "Client updated successfully"
}
```

**How to call from Next.js**:
```typescript
const response = await fetch(`https://your-cocobase-api.com/oauth/clients/${clientId}`, {
  method: 'PUT',
  headers: {
    'Authorization': `Bearer ${authToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: updatedName,
    redirect_uris: updatedUris,
    // Only include fields you want to update
  })
});

const updated = await response.json();
```

---

### 5. Delete OAuth Client

```bash
DELETE /oauth/clients/{client_id}
Authorization: Bearer <your_auth_token>
```

**Important**: This will:
- Delete the OAuth client
- Revoke ALL access tokens for this client
- Revoke ALL refresh tokens for this client
- Invalidate ALL authorization codes
- Delete ALL user consents

**Response**:
```json
{
  "message": "OAuth client deleted successfully",
  "client_id": "client_abc123"
}
```

**How to call from Next.js**:
```typescript
const confirmDelete = confirm(
  'Are you sure? This will revoke all tokens and cannot be undone.'
);

if (confirmDelete) {
  const response = await fetch(`https://your-cocobase-api.com/oauth/clients/${clientId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json'
    }
  });

  if (response.ok) {
    const result = await response.json();
    console.log(result.message);
    // Refresh the client list
  }
}
```

---

## Important Security Notes

1. **Client Secret**: Only shown ONCE during creation. Your UI MUST:
   - Display a clear warning that it's shown only once
   - Provide a copy-to-clipboard button
   - Force user to confirm they've saved it before closing

2. **Authentication**: All API calls require `Authorization: Bearer <token>` header

3. **Redirect URIs**:
   - Must be exact matches (no wildcards)
   - Must use `http://` or `https://`
   - `http://localhost` is allowed for development only
   - Production URIs must use HTTPS

4. **Authorization**: Users can only manage their own OAuth clients (enforced by API)

---

## Common Integration Patterns

### Pattern 1: List Clients on Dashboard Load

```typescript
useEffect(() => {
  async function loadClients() {
    const response = await fetch('https://api.cocobase.com/oauth/clients', {
      headers: {
        'Authorization': `Bearer ${authToken}`,
        'Content-Type': 'application/json'
      }
    });

    if (response.ok) {
      const data = await response.json();
      setClients(data.clients);
    }
  }

  loadClients();
}, [authToken]);
```

### Pattern 2: Create Client with Form

```typescript
async function handleCreateClient(formData) {
  const response = await fetch('https://api.cocobase.com/oauth/clients', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      name: formData.name,
      description: formData.description,
      redirect_uris: formData.redirect_uris.split(',').map(s => s.trim()),
      scopes: ['openid', 'email', 'profile'],
      is_confidential: true
    })
  });

  if (response.ok) {
    const newClient = await response.json();

    // CRITICAL: Show client_secret to user immediately
    alert(`Save this client secret NOW:\n${newClient.client_secret}`);

    // Or better - show in a modal with copy button
    showSecretModal(newClient.client_id, newClient.client_secret);
  } else {
    const error = await response.json();
    alert(`Error: ${error.detail}`);
  }
}
```

### Pattern 3: Update Client Settings

```typescript
async function updateClientRedirectUris(clientId, newUris) {
  const response = await fetch(`https://api.cocobase.com/oauth/clients/${clientId}`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      redirect_uris: newUris  // Only update redirect URIs
    })
  });

  if (response.ok) {
    const updated = await response.json();
    console.log(updated.message); // "Client updated successfully"
  }
}
```

### Pattern 4: Delete Client with Confirmation

```typescript
async function deleteClient(clientId, clientName) {
  const confirmed = window.confirm(
    `Delete "${clientName}"?\n\n` +
    'This will:\n' +
    '- Revoke all access tokens\n' +
    '- Revoke all refresh tokens\n' +
    '- Invalidate all authorization codes\n' +
    '- Delete all user consents\n\n' +
    'This action cannot be undone.'
  );

  if (!confirmed) return;

  const response = await fetch(`https://api.cocobase.com/oauth/clients/${clientId}`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${authToken}`,
      'Content-Type': 'application/json'
    }
  });

  if (response.ok) {
    const result = await response.json();
    alert(result.message);
    // Refresh client list
    loadClients();
  }
}
```

---

## Error Handling

All API endpoints return standard HTTP status codes:

- **200 OK**: Request successful
- **400 Bad Request**: Invalid request data (check `detail` in response)
- **401 Unauthorized**: Missing or invalid auth token
- **403 Forbidden**: Not authorized to access this client
- **404 Not Found**: Client not found

**Example error response**:
```json
{
  "detail": "Invalid redirect URIs"
}
```

**Error handling pattern**:
```typescript
const response = await fetch(url, options);

if (!response.ok) {
  const error = await response.json();
  throw new Error(error.detail || 'Request failed');
}

const data = await response.json();
```

---

## What Your Users Do Next

After creating OAuth clients through your UI, your users will:

1. **Use the credentials** in their applications:
   - `client_id`: Public identifier
   - `client_secret`: Private secret (never expose in frontend code)

2. **Implement OAuth flow** in their apps:
   - Redirect users to: `https://cocobase.com/oauth/authorize?response_type=code&client_id=<client_id>&redirect_uri=<uri>&scope=openid email profile`
   - Receive authorization code at redirect URI
   - Exchange code for access token at: `POST /oauth/token`
   - Use access token to call APIs: `Authorization: Bearer <token>`

3. **Test the integration**:
   - Use `http://localhost:3000/callback` for local development
   - Update to production HTTPS URIs when deploying

---

## Summary

You need to build UI that calls these 5 endpoints:

1. `GET /oauth/clients` - List all clients
2. `GET /oauth/clients/{client_id}` - Get single client
3. `POST /oauth/clients` - Create new client (shows secret once!)
4. `PUT /oauth/clients/{client_id}` - Update client settings
5. `DELETE /oauth/clients/{client_id}` - Delete client (with confirmation)

All endpoints require authentication and return JSON responses. The most critical part is handling the `client_secret` on creation - it's only shown once and must be saved by the user immediately.
