"""
Cron Job Model - Persistent Recurring Tasks

Cron jobs are created from the UI and run on a schedule.
They're stored in the database and execute cloud functions periodically.
"""

from sqlalchemy import Column, String, Boolean, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import uuid

from app.core.database import Base



class CronJob(Base):
    """
    Persistent cron job that executes cloud functions on a schedule.

    Created from UI, not from cloud function code.
    """
    __tablename__ = "cron_jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, index=True)

    # Cron details
    name = Column(String(255))
    description = Column(String(1000), nullable=True)

    # Cloud function to call
    function_name = Column(String(255))  # "email-service" or "email-service.send_bulk"

    # When to run
    cron_expression = Column(String(100))  # "0 9 * * *" = 9 AM every day
    timezone = Column(String(50), default="UTC")

    # Optional payload (if no req.body, use this)
    payload = Column(JSON, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Last execution
    last_run_at = Column(DateTime, nullable=True)
    last_status = Column(String, nullable=True)  # "success" or "failed"
    last_error = Column(String, nullable=True)

    # Metrics
    total_runs = Column(Integer, default=0)
    failed_runs = Column(Integer, default=0)


class CronJobRun(Base):
    """
    Record of each cron job execution.

    Stores details about when the job ran and what happened.
    """
    __tablename__ = "cron_job_runs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cron_job_id = Column(String, ForeignKey("cron_jobs.id"))

    # When it ran
    ran_at = Column(DateTime, default=datetime.utcnow)
    duration_ms = Column(Integer, nullable=True)  # How long it took

    # Result
    status = Column(String)  # "success" or "failed"
    result = Column(JSON, nullable=True)  # Return value from function
    error = Column(String, nullable=True)  # Error message if failed

    # Context
    function_name = Column(String(255))
    payload = Column(JSON)
