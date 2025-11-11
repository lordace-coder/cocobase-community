# Cron Jobs - Quick Reference

## Current Jobs

| Job ID | Schedule | What it does |
|--------|----------|--------------|
| `check_expired_subscriptions` | Daily 2:00 AM UTC | Downgrades expired subscriptions to free plan |

## Quick Commands

### Check Status
```bash
GET /cron/status
```

### Trigger Manually
```bash
POST /cron/check-subscriptions
# or
POST /cron/trigger/check_expired_subscriptions
```

### Test Scheduler
```bash
.venv/bin/python test_scheduler.py
```

## Expected Behavior

**On Application Start:**
```
INFO - Initializing background scheduler...
INFO - ✓ Scheduled: check_expired_subscriptions (daily at 2:00 AM UTC)
INFO - ✓ Background scheduler started successfully
INFO - Active scheduled jobs: 1
```

**When Job Runs:**
```
INFO - Running scheduled job: check_expired_subscriptions
INFO - Starting expired subscription check...
INFO - ✓ Successfully downgraded X projects to Free plan
INFO - Expired subscriptions check complete.
```

## Files

- [app/core/scheduler.py](app/core/scheduler.py) - Scheduler implementation
- [app/cron/payments.py](app/cron/payments.py) - Subscription expiry logic
- [app/cron/cron.py](app/cron/cron.py) - API endpoints
- [CRON_JOBS.md](CRON_JOBS.md) - Full documentation

## Troubleshooting

**Not running?** Check `/cron/status` endpoint

**Need to run now?** Use `POST /cron/check-subscriptions`

**Add more jobs?** See [CRON_JOBS.md](CRON_JOBS.md#adding-new-cron-jobs)
