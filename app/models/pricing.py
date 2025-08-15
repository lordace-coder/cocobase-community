from datetime import datetime
from sqlalchemy import (
    Column,
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
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PricingPlan(Base):
    __tablename__ = "pricing_plans"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False, unique=True)
    description = Column(String(255))
    price = Column(Float, nullable=False, default=0.0)
    currency = Column(String(10), nullable=False, default="USD")

    # Limits
    max_requests_per_month = Column(Integer)
    max_storage_mb = Column(Integer)
    max_projects = Column(Integer)
    max_users = Column(Integer)  # NEW: number of allowed users in the project

    # Features
    features = Column(JSON)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    projects = relationship("ProjectSubscription", back_populates="plan")


class ProjectSubscription(Base):
    __tablename__ = "project_subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("projects.id"), nullable=False
    )  # Uses your existing Project model
    plan_id = Column(Integer, ForeignKey("pricing_plans.id"), nullable=False)

    start_date = Column(DateTime(timezone=True), server_default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    auto_renew = Column(Boolean, default=True)

    plan = relationship("PricingPlan", back_populates="projects")

    def check_and_downgrade(self, db, free_plan_id: int):
        """Downgrade project to free plan if expired."""
        now = datetime.utcnow()
        if self.end_date and self.end_date < now and not self.auto_renew:
            self.plan_id = free_plan_id
            self.is_active = True  # Still active, but on free plan
            db.commit()
            return True
        return False
