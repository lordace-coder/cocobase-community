from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    ForeignKey,
    Boolean,
    DateTime,
    JSON,
    Enum,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from uuid import uuid4
from app.core.database import Base


class RuntimeEnum(str, enum.Enum):
    PYTHON = "python3.10"
    NODE = "node18"
    GO = "go1.20"
    # Add more supported runtimes


class CloudFunction(Base):
    __tablename__ = "cloud_functions"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))  # UUID
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)

    name = Column(String(100), nullable=False)  # unique per project
    description = Column(Text, nullable=True)

    runtime = Column(Enum(RuntimeEnum), nullable=False)
    code = Column(
        Text, nullable=False
    )  # store inline code (or store a path to file/object storage)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # relationships
    executions = relationship(
        "FunctionExecution", back_populates="function", cascade="all, delete-orphan"
    )


class FunctionExecution(Base):
    __tablename__ = "function_executions"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))  # UUID
    function_id = Column(String, ForeignKey("cloud_functions.id"), nullable=False)

    status = Column(String(50), nullable=False)  # success, failed, timeout
    logs = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)

    triggered_by = Column(String, nullable=True)  # manual, http, schedule, db-event
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relationship
    function = relationship("CloudFunction", back_populates="executions")
