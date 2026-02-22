# Email Fallback System - Quick Reference

## TL;DR

**Your users DON'T need to configure email to use password reset!** Cocobase automatically handles it.

---

## How It Works

Cocobase uses a **3-tier priority system** for sending emails:

```
1. Project Integration (Resend/Cocomailer/EmailJS)
   ↓ (if not configured)
2. SMTP Configuration
   ↓ (if not configured)
3. Cocobase Fallback (noreply@cocobase.buzz)
   ✅ ALWAYS WORKS
```

---

## Implementation Details

### Location
File: [app/services/email_service.py](app/services/email_service.py#L69-L121)

### Method
`EmailService.get_active_provider()`

### Fallback Configuration
```python
{
    'type': 'cocobase_fallback',
    'provider': 'resend',
    'api_key': os.getenv('COCOBASE_RESEND_API_KEY'),
    'from_email': 'noreply@cocobase.buzz',
    'from_name': 'Cocobase'
}
```

### Email Sending
File: [app/services/email_service.py](app/services/email_service.py#L197-L223)

Uses Resend API directly via `httpx`:
```python
async with httpx.AsyncClient() as client:
    response = await client.post(
        'https://api.resend.com/emails',
        headers={'Authorization': f'Bearer {resend_api_key}'},
        json={
            'from': 'Cocobase <noreply@cocobase.buzz>',
            'to': recipients,
            'subject': subject,
            'html': body,
        }
    )
```

---

## Environment Variables

### Required
```bash
COCOBASE_RESEND_API_KEY=your_resend_api_key
```

Already set in `.env` file.

---

## User Experience

### For Projects WITHOUT Email Config
1. User requests password reset
2. Cocobase sends email from `noreply@cocobase.buzz`
3. Email includes link to Cocobase-hosted reset page
4. User resets password
5. Confirmation email sent from `noreply@cocobase.buzz`

### For Projects WITH Email Config
1. User requests password reset
2. Email sent from **their configured provider/email**
3. Email includes link (to their page or Cocobase page, based on config)
4. User resets password
5. Confirmation email sent from **their configured provider/email**

---

## Benefits

✅ **Zero Barrier to Entry**
- Users can test password reset immediately
- No setup required

✅ **Production Ready**
- Professional emails from day one
- No "coming soon" features

✅ **Seamless Upgrade Path**
- Users can configure their own email anytime
- Automatic switch from fallback to custom

✅ **No Breaking Changes**
- Existing projects with email continue working
- New projects work automatically

---

## Testing

### Test Without Email Config
```bash
# 1. Create project without email integration/SMTP
POST /projects

# 2. Create user
POST /auth-collections/signup

# 3. Request password reset
POST /auth-collections/forgot-password
{
  "email": "user@example.com"
}

# ✅ Email sent via Cocobase fallback (noreply@cocobase.buzz)
```

### Test With Custom Email
```bash
# 1. Configure project integration
POST /integrations/resend
{
  "api_key": "re_your_key",
  "from_email": "noreply@yourapp.com"
}

# 2. Request password reset
POST /auth-collections/forgot-password

# ✅ Email sent via custom integration (noreply@yourapp.com)
```

---

## Monitoring

All emails (including fallback) are logged in the `email_logs` table:
- Recipients
- Subject
- Template used
- Status (sent/failed)
- Error messages
- Timestamp

Query fallback emails:
```sql
SELECT * FROM email_logs
WHERE project_id = 'project_id'
ORDER BY created_at DESC;
```

---

## Dependencies

- `httpx` - For Resend API calls (already in requirements.txt)
- `COCOBASE_RESEND_API_KEY` - Environment variable (already in .env)

---

## Error Handling

If fallback email fails:
```python
if response.status_code != 200:
    raise Exception(f"Cocobase fallback email failed: {response.text}")
```

Email log will show:
- Status: `FAILED`
- Error message: Response from Resend

---

## Future Enhancements

Potential improvements:
- [ ] Rate limiting on fallback emails
- [ ] Usage analytics/dashboard
- [ ] Option to disable fallback (force users to configure)
- [ ] Custom branding in fallback emails per project
- [ ] Fallback email quota per project

---

## Related Files

- [app/services/email_service.py](app/services/email_service.py) - Email service with fallback
- [.env](.env) - Environment variables
- [PASSWORD_RESET_SUMMARY.md](PASSWORD_RESET_SUMMARY.md) - Complete feature docs
- [FORGOT_PASSWORD_SETUP.md](FORGOT_PASSWORD_SETUP.md) - Setup guide
