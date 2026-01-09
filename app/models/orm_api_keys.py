from datetime import datetime
from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    DateTime,
    Index,
    Boolean,
    Integer,
    func,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import uuid

from app.services.utils import hash_password, verify_password


class ORMApiKey(Base):
    """
    ORM API Keys for secure project-scoped database access.

    Format: coco_orm_<project_id>_<random_32_chars>
    Example: coco_orm_901235c6-9564-4de0-bb40_8a7f3e9d2c1b4f6a8e5d7c9b3a1f2e4d
    """
    __tablename__ = "orm_api_keys"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id = Column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    key_hash = Column(String, nullable=False)  # bcrypt hash of the key
    key_prefix = Column(String, nullable=False)  # first 16 chars for identification
    name = Column(String, nullable=False)  # user-defined name
    permissions = Column(JSON, nullable=False, default=dict)  # granular permissions
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)

    # Relationships
    project = relationship("Project")
    creator = relationship("User")

    __table_args__ = (
        Index("idx_orm_keys_project", "project_id"),
        Index("idx_orm_keys_prefix", "key_prefix"),
        Index("idx_orm_keys_active", "is_active", "project_id"),
    )

    def set_key(self, key: str) -> None:
        """Hash the API key for secure storage."""
        self.key_hash = hash_password(key)
        self.key_prefix = key[:16]  # Store first 16 chars for display

    def verify_key(self, key: str) -> bool:
        """Verify if the provided key matches the stored hash."""
        return verify_password(key, self.key_hash)

    def __repr__(self):
        return f"<ORMApiKey {self.name} ({self.key_prefix}...)>"