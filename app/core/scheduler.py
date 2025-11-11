"""
Background task scheduler for automated jobs.

This module sets up and manages scheduled background tasks using APScheduler.
"""

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
import logging

from app.core.database import get_db
from app.cron.payments import auto_downgrade_expired_projects

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = None


def check_expired_subscriptions_job():
    """
    Job to check and downgrade expired project subscriptions.
    Runs as a scheduled background task.
    """
    logger.info("Running scheduled job: check_expired_subscriptions")

    try:
        db = next(get_db())

        # Run the downgrade function
        downgraded_count = auto_downgrade_expired_projects(db)

        logger.info(
            f"Expired subscriptions check complete. "
            f"Downgraded {downgraded_count} projects."
        )

        db.close()

    except Exception as e:
        logger.error(f"Error in check_expired_subscriptions_job: {e}", exc_info=True)


def start_scheduler():
    """
    Start the background scheduler and add all scheduled jobs.

    This should be called once when the application starts.
    """
    global scheduler

    if scheduler is not None:
        logger.warning("Scheduler already running, skipping initialization")
        return

    logger.info("Initializing background scheduler...")

    # Create scheduler instance
    scheduler = BackgroundScheduler(
        timezone="UTC",
        job_defaults={
            'coalesce': True,  # Combine multiple pending executions into one
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 300  # 5 minutes grace time for misfired jobs
        }
    )

    # Add scheduled jobs

    # Job 1: Check expired subscriptions daily at 2 AM UTC
    scheduler.add_job(
        func=check_expired_subscriptions_job,
        trigger=CronTrigger(hour=2, minute=0),  # Daily at 2:00 AM UTC
        id='check_expired_subscriptions',
        name='Check and downgrade expired subscriptions',
        replace_existing=True
    )
    logger.info("✓ Scheduled: check_expired_subscriptions (daily at 2:00 AM UTC)")

    # Optional: Also run every 6 hours for more frequent checks
    # Uncomment if you want more frequent checks:
    # scheduler.add_job(
    #     func=check_expired_subscriptions_job,
    #     trigger=IntervalTrigger(hours=6),
    #     id='check_expired_subscriptions_interval',
    #     name='Check expired subscriptions (interval)',
    #     replace_existing=True
    # )

    # Start the scheduler
    scheduler.start()
    logger.info("✓ Background scheduler started successfully")

    # Log all scheduled jobs
    jobs = scheduler.get_jobs()
    logger.info(f"Active scheduled jobs: {len(jobs)}")
    for job in jobs:
        logger.info(f"  - {job.name} (ID: {job.id}, Next run: {job.next_run_time})")


def stop_scheduler():
    """
    Gracefully stop the scheduler.

    This should be called when the application shuts down.
    """
    global scheduler

    if scheduler is None:
        logger.warning("Scheduler not running")
        return

    logger.info("Stopping background scheduler...")
    scheduler.shutdown(wait=True)
    scheduler = None
    logger.info("✓ Background scheduler stopped")


def get_scheduler_status():
    """
    Get the current status of the scheduler and its jobs.

    Returns:
        dict: Status information including running jobs and next run times
    """
    if scheduler is None:
        return {
            "running": False,
            "jobs": []
        }

    jobs_info = []
    for job in scheduler.get_jobs():
        jobs_info.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            "trigger": str(job.trigger)
        })

    return {
        "running": scheduler.running,
        "jobs": jobs_info,
        "total_jobs": len(jobs_info)
    }


def run_job_now(job_id: str):
    """
    Manually trigger a scheduled job to run immediately.

    Args:
        job_id: The ID of the job to run

    Returns:
        bool: True if job was triggered successfully
    """
    if scheduler is None:
        logger.error("Scheduler not running")
        return False

    try:
        job = scheduler.get_job(job_id)
        if job is None:
            logger.error(f"Job not found: {job_id}")
            return False

        logger.info(f"Manually triggering job: {job_id}")
        job.modify(next_run_time=datetime.now())
        return True

    except Exception as e:
        logger.error(f"Error triggering job {job_id}: {e}", exc_info=True)
        return False
