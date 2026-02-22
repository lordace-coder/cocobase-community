from datetime import datetime
from sqlalchemy import (
    Column,
    ForeignKey,
    String,
    DateTime,
    Boolean,
    Text,
    JSON,
    func,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import uuid


class Integration(Base):
    """
    Available integrations in the system.
    These are predefined integrations that users can enable.
    """
    __tablename__ = "integrations"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    icon_url: Mapped[str] = mapped_column(String, nullable=True)
    
    # Python module information
    module_name: Mapped[str] = mapped_column(String, nullable=True)  # e.g., "openai_integration"
    module_code: Mapped[str] = mapped_column(Text, nullable=True)  # Actual Python code
    
    # Configuration schema (defines what config fields are needed)
    config_schema = Column(JSON, nullable=True)  # e.g., {"api_key": "string", "region": "string"}
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    project_integrations = relationship(
        "ProjectIntegration", back_populates="integration", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Integration {self.name}>"


class ProjectIntegration(Base):
    """
    Integrations enabled for a specific project.
    User turns on integration for project and optionally sets config.
    """
    __tablename__ = "project_integrations"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id: Mapped[str] = mapped_column(
        String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    integration_id: Mapped[str] = mapped_column(
        String, ForeignKey("integrations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    
    # User's configuration for this integration (optional)
    config = Column(JSON, default=dict)
    
    # Is this integration currently enabled?
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    project = relationship("Project", back_populates="integrations")
    integration = relationship("Integration", back_populates="project_integrations")

    __table_args__ = (
        UniqueConstraint("project_id", "integration_id", name="uq_project_integration"),
    )

    def __repr__(self):
        return f"<ProjectIntegration project={self.project_id} integration={self.integration_id}>"

