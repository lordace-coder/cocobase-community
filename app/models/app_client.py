from datetime import datetime
from sqlalchemy import (
    PickleType,
    Column,
    ForeignKey,
    String,
    DateTime,
    Index,
    JSON,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import uuid

from app.services.utils import hash_password, verify_password


class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    api_key = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    owner = relationship("User", back_populates="projects")
    collections = relationship(
        "Collection", back_populates="project", cascade="all, delete-orphan"
    )
    allowed_origins = Column(PickleType, nullable=True)


class AppUser(Base):
    __tablename__ = "app_users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    client_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    data = Column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    oauth_id: Mapped[str] = mapped_column(String, nullable=True, unique=True)

    __table_args__ = (UniqueConstraint("client_id", "email", name="uq_client_email"),)

    def set_password(self, password: str) -> None:
        self.password_hash = hash_password(password)

    def compare_password(self, password: str) -> bool:
        return verify_password(password, self.password_hash)
