# CocoBase API Documentation

Complete documentation for the CocoBase API.

**Base URL:** `https://api.cocobase.buzz`

---

## Documentation Index

### Core APIs
1. **[Collections API](./collections.md)** - Store and query JSON documents
2. **[Auth Collections](./auth-collections.md)** - User authentication and management
3. **[Storage API](./storage.md)** - File upload and management

### Advanced Features
4. **[Realtime](./realtime.md)** - WebSocket features (collection watch, broadcast, rooms)
5. **[Filtering Guide](./filtering.md)** - Complete filtering and querying guide
6. **[Relationships](./relationships.md)** - Document relationships and population

---

## Quick Start

### 1. Get Your API Key
```
Dashboard → Project Settings → API Keys
```

### 2. Create Your First Collection
```bash
curl -X POST https://api.cocobase.buzz/collections/users/documents \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "email": "john@example.com"}'
```

### 3. Query Documents
```bash
curl "https://api.cocobase.buzz/collections/users/documents?name_contains=john" \
  -H "X-API-Key: your-api-key"
```

### 4. Connect to Realtime
```javascript
const ws = new WebSocket('wss://api.cocobase.buzz/realtime/collections/users');
ws.onopen = () => {
  ws.send(JSON.stringify({
    api_key: "your-api-key",
    filters: { status: "active" }
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Real-time event:', data);
};
```

---

## Authentication

All API requests require your project API key:

```bash
-H "X-API-Key: your-api-key-here"
```

For auth-collection endpoints, authenticated users also need:

```bash
-H "Authorization: Bearer jwt-token-here"
```

---

## Support

- **Email:** support@cocobase.com
- **Website:** https://cocobase.buzz
- **GitHub Issues:** https://github.com/cocobase/issues

---

**Happy Building! 🚀**
