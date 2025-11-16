from datetime import datetime
from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    DateTime,
    Index,
    Boolean,
    Table,
    UniqueConstraint,
    func,
    JSON,
    BigInteger,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB,ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import uuid

from app.services.utils import hash_password, verify_password

# Association table for shared projects
project_shares = Table(
    "project_shares",
    Base.metadata,
    Column("project_id", String, ForeignKey("projects.id"), primary_key=True),
    Column("user_id", String, ForeignKey("users.id"), primary_key=True),
    Column("shared_at", DateTime, server_default=func.now()),
)


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    api_key = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    allowed_origins = Column(ARRAY(String), default=lambda: [], server_default="{}")
    callback_url = Column(String, nullable=True)
    configs = Column(JSON, default=dict)
    integrations = relationship("ProjectIntegration", back_populates="project")

    # Relationships
    owner = relationship("User", back_populates="projects")
    collections = relationship(
        "Collection", back_populates="project", cascade="all, delete-orphan"
    )
    shared_with = relationship(
        "User", secondary=project_shares, back_populates="shared_projects"
    )
    subscriptions = relationship(
        "ProjectSubscription", back_populates="project", cascade="all, delete-orphan"
    )
    payments = relationship("Payment", back_populates="project")
    active = Column(Boolean, default=True)

    # Storage tracking (OPTIMIZED: cached to avoid listing all files)
    storage_used_bytes = Column(BigInteger, nullable=True, default=0, server_default="0")
    storage_last_updated = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"{self.name} owned by {self.user_id}"


class AppUser(Base):
    __tablename__ = "app_users"
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    data = Column(JSONB, nullable=True, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    oauth_id: Mapped[str] = mapped_column(String, nullable=True, unique=True)
    oauth_provider: Mapped[str] = mapped_column(String, nullable=True)  # 'google', 'apple', etc.
    roles = Column(ARRAY(String), default=lambda: [], server_default="{}")

    __table_args__ = (
        UniqueConstraint("client_id", "email", name="uq_client_email"),
        Index("ix_app_users_created_at", "created_at"),
        Index("ix_app_users_oauth_id", "oauth_id"),  # OPTIMIZED: Index for OAuth lookups
        Index(
            "ix_app_users_data_gin",
            "data",
            postgresql_using="gin",
            postgresql_ops={"data": "jsonb_path_ops"},
        ),
    )

    def set_password(self, password: str) -> None:
        self.password = hash_password(password)

    def compare_password(self, password: str) -> bool:
        return verify_password(password, self.password)
