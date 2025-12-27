from fastapi import APIRouter, Depends, HTTPException

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.cron.payments import auto_downgrade_expired_projects
from app.core.scheduler import get_scheduler_status, run_job_now
from app.models.user import User


router = APIRouter(prefix="/cron", tags=["Cron Jobs"])


@router.get("/status")
def get_cron_status():
    """
    Get the status of all scheduled cron jobs.

    Requires authentication. Shows which jobs are scheduled and when they'll run next.
    """
    status = get_scheduler_status()

    if not status["running"]:
        return {
            "status": "stopped",
            "message": "Background scheduler is not running",
            "jobs": [],
        }

    return {
        "status": "running",
        "total_jobs": status["total_jobs"],
        "jobs": status["jobs"],
    }


@router.post("/trigger/{job_id}")
def trigger_job(job_id: str, ):
    """
    Manually trigger a scheduled job to run immediately.

    Requires authentication. Useful for testing or running jobs on-demand.
    """
    success = run_job_now(job_id)

    if not success:
        raise HTTPException(
            status_code=404, detail=f"Job '{job_id}' not found or scheduler not running"
        )

    return {"message": f"Job '{job_id}' triggered successfully", "job_id": job_id}


@router.post("/check-subscriptions")
def manual_check_subscriptions(
    db=Depends(get_db), 
):
    """
    Manually check and downgrade expired subscriptions.

    This endpoint allows you to manually trigger the subscription check
    instead of waiting for the scheduled job. Requires authentication.

    Note: This job runs automatically daily at 2:00 AM UTC.
    """
    try:
        downgraded_count = auto_downgrade_expired_projects(db)

        return {
            "success": True,
            "message": "Subscription check completed",
            "downgraded_projects": downgraded_count,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error checking subscriptions: {str(e)}"
        )
