from sqlalchemy import Column, String, DateTime, Index, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import uuid
from datetime import datetime


class Collection(Base):
    __tablename__ = "collections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)

    project = relationship("Project", back_populates="collections")
    documents = relationship(
        "Document",
        back_populates="collection",
        cascade="all, delete-orphan",
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    collection_id = Column(
        String,
        ForeignKey("collections.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    data = Column(JSON, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    collection = relationship("Collection", back_populates="documents")

    __table_args__ = (Index("ix_documents_data_gin", "data", postgresql_using="gin"),)
