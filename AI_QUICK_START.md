# AI Assistant Quick Start Guide

## 🚀 Setup (3 steps)

### 1. Run Migration
```bash
source .venv/bin/activate
alembic upgrade head
```

### 2. Set Fine-Tuned Model (Optional)
```bash
export AI_MODEL=ft:gpt-4o-mini-2024-07-18:your-org:cocobase-v2:xxxxx
```

### 3. Restart Server
```bash
uvicorn app.main:app --reload
```

## 💬 Usage Examples

### Basic Code Generation
```python
import requests

response = requests.post(
    "http://localhost:8000/ai-assistant/{project_id}/generate",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={"prompt": "Create a function to list users"}
)

print(response.json()['code'])
print(response.json()['rate_limit'])  # Check remaining quota
```

### With Conversation History
```python
# First request
response1 = requests.post(
    "http://localhost:8000/ai-assistant/{project_id}/generate",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={"prompt": "Create a function to list users"}
)

session_id = response1.json()['session_id']

# Follow-up request - AI remembers context!
response2 = requests.post(
    "http://localhost:8000/ai-assistant/{project_id}/generate",
    headers={"Authorization": "Bearer YOUR_TOKEN"},
    json={
        "prompt": "Add pagination to that function",
        "session_id": session_id  # Use same session_id
    }
)
```

### Check Quota
```python
response = requests.get(
    "http://localhost:8000/ai-assistant/{project_id}/rate-limit",
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

quota = response.json()
print(f"Remaining: {quota['remaining']}/{quota['limit']}")
print(f"Resets at: {quota['reset_time']}")
```

## ⚙️ Rate Limits

| Plan | Chats/Hour | History Messages |
|------|------------|------------------|
| Free | 10 | 5 |
| Paid | 30 | 10 |
| Premium | 100 | 20 |

## 🔧 Customization

Edit limits in `app/services/ai_assistant/bot_with_history.py`:

```python
RATE_LIMITS = {
    'free': {
        'chats_per_hour': 10,  # Change this
        'max_history': 5,
    },
    # ...
}
```

## 📊 Monitoring

### View Usage Stats
```bash
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/ai-assistant/{project_id}/usage-stats?hours=24"
```

### View Conversation
```bash
curl -H "Authorization: Bearer TOKEN" \
  "http://localhost:8000/ai-assistant/{project_id}/conversation/{session_id}"
```

## ❓ Troubleshooting

**Rate limit exceeded?**
- Wait until reset time (hourly)
- Upgrade to paid plan for more chats

**No conversation history?**
- Make sure you're passing the same `session_id`
- Check session exists: `GET /conversation/{session_id}`

**Migration errors?**
- Run: `alembic downgrade -1` then `alembic upgrade head`
- Check database connection

## 📝 Full Documentation

See [AI_ASSISTANT_UPGRADE_SUMMARY.md](./AI_ASSISTANT_UPGRADE_SUMMARY.md) for complete details.
