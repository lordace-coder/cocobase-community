"""
AI Assistant Models - Conversation history and rate limiting
"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Index,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.core.database import Base


class AIConversation(Base):
    """Stores AI assistant conversations for history tracking"""
    __tablename__ = "ai_conversations"

    id = Column(Integer, primary_key=True, index=True)

    # Relationships
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)  # Optional: track which user

    # Conversation context
    session_id = Column(String(100), nullable=False, index=True)  # Groups related messages
    message_type = Column(String(20), nullable=False)  # 'system', 'user', 'assistant'
    content = Column(Text, nullable=False)

    # Metadata
    function_name = Column(String(255), nullable=True)  # Which function was being edited/created
    code_generated = Column(Text, nullable=True)  # The actual code generated (if any)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    project = relationship("Project", backref="ai_conversations")

    __table_args__ = (
        Index("idx_project_session", "project_id", "session_id"),
        Index("idx_project_created", "project_id", "created_at"),
    )


class AIUsageCounter(Base):
    """Tracks AI assistant usage per project per hour for rate limiting"""
    __tablename__ = "ai_usage_counters"

    id = Column(Integer, primary_key=True)

    # Relationships
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)

    # Time tracking (hourly buckets)
    hour_bucket = Column(DateTime(timezone=True), nullable=False, index=True)  # Rounded to hour

    # Usage counts
    chat_count = Column(Integer, default=0, nullable=False)
    code_generation_count = Column(Integer, default=0, nullable=False)
    question_count = Column(Integer, default=0, nullable=False)

    # Metadata
    last_request_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    project = relationship("Project", backref="ai_usage")

    __table_args__ = (
        Index("idx_project_hour", "project_id", "hour_bucket", unique=True),
    )

    @staticmethod
    def get_current_hour_bucket():
        """Get current hour bucket (rounded down to the hour)"""
        now = datetime.now(timezone.utc)
        return now.replace(minute=0, second=0, microsecond=0)
