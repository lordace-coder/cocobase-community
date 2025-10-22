from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Index,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.app_client import Project
from sqlalchemy.orm import Session


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)

    # Reference information
    reference = Column(String(255), unique=True, nullable=False, index=True)
    provider = Column(
        String(20), nullable=False, default="paystack"
    )  # paystack, stripe, flutterwave

    # Amount details
    amount = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default="NGN")

    # Status tracking
    status = Column(
        String(20), nullable=False, default="pending", index=True
    )  # pending, success, failed, cancelled

    # Relationships
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    user_id = Column(
        String(100), ForeignKey("users.id"), nullable=False
    )  # User who made payment
    plan_id = Column(Integer, ForeignKey("pricing_plans.id"), nullable=False)
    subscription_id = Column(
        Integer, ForeignKey("project_subscriptions.id"), nullable=True
    )

    # Payment metadata
    payment_metadata = Column(JSON)
    provider_response = Column(JSON)  # Store full response from payment provider

    # Webhook tracking
    webhook_received = Column(Boolean, default=False)
    webhook_received_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    project = relationship("Project", back_populates="payments")
    user = relationship("User", back_populates="payments")
    plan = relationship("PricingPlan")
    subscription = relationship("ProjectSubscription", back_populates="payments")

    def __repr__(self):
        return (
            f"Payment({self.reference}, {self.status}, {self.amount} {self.currency})"
        )


# Update PricingPlan model
class PricingPlan(Base):
    __tablename__ = "pricing_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(255))
    price = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), nullable=False, default="USD")
    duration_days = Column(
        Integer, nullable=True, default=30
    )  # Added for flexible durations

    # Limits
    max_requests_per_month = Column(Integer)
    max_storage_mb = Column(Integer)
    max_users = Column(Integer)
    max_cloud_functions = Column(Integer)

    # Features
    features = Column(JSON)
    is_active = Column(Boolean, default=True)
    is_free = Column(Boolean, default=False)  # Mark free plans

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    projects = relationship("ProjectSubscription", back_populates="plan")

    def __repr__(self):
        return self.name


# Update ProjectSubscription model
class ProjectSubscription(Base):
    __tablename__ = "project_subscriptions"

    id = Column(Integer, primary_key=True, index=True)

    # Relationships
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("pricing_plans.id"), nullable=False)

    # Subscription details
    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    auto_renew = Column(Boolean, default=True)

    # Grace period (days after expiry before downgrade)
    grace_period_days = Column(Integer, default=3)

    # Relationships
    plan = relationship("PricingPlan", back_populates="projects")
    project = relationship("Project", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription")

    def check_and_downgrade(self, db, free_plan_id: int):
        """Downgrade project to free plan if expired and past grace period."""
        from datetime import timedelta

        now = datetime.utcnow()
        if self.end_date:
            grace_end = self.end_date + timedelta(days=self.grace_period_days)
            if grace_end < now and not self.auto_renew:
                self.plan_id = free_plan_id
                self.is_active = True
                db.commit()
                return True
        return False

    def is_expired(self):
        if self.end_date is None:
            return False  # No end date means never expires

        # Use timezone-aware datetime
        now = datetime.now(timezone.utc)

        # Make end_date timezone-aware if it isn't already
        if self.end_date.tzinfo is None:
            end_date = self.end_date.replace(tzinfo=timezone.utc)
        else:
            end_date = self.end_date

        return now > end_date

    def days_remaining(self):
        if self.end_date is None:
            return None  # or float('inf') for unlimited

        # Use timezone-aware datetime
        now = datetime.now(timezone.utc)

        # Make end_date timezone-aware if it isn't already
        if self.end_date.tzinfo is None:
            end_date = self.end_date.replace(tzinfo=timezone.utc)
        else:
            end_date = self.end_date

        delta = end_date - now
        return delta.days

    def __repr__(self):
        return f"{self.plan.name} plan for {self.project.name}"


def get_current_plan(project: Project, db: Session) -> PricingPlan:
    active_sub = (
        db.query(ProjectSubscription)
        .filter(
            ProjectSubscription.project_id == project.id,
            ProjectSubscription.is_active == True,
        )
        .order_by(ProjectSubscription.start_date.desc())
        .first()
    )
    return (
        active_sub.plan
        if active_sub
        else db.query(PricingPlan).filter_by(is_free=True).first()
    )



class ApiUsageCounter(Base):
    __tablename__ = "api_usage_counters"
    
    id = Column(Integer, primary_key=True)
    project_id = Column(String, nullable=False, index=True)
    month = Column(String(7), nullable=False)  # Format: "2025-10"
    request_count = Column(Integer, default=0, nullable=False)
    last_synced_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_project_month', 'project_id', 'month', unique=True),
    )