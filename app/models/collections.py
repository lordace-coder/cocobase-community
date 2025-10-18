from sqlalchemy import Column, String, DateTime, Index, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
import uuid
from datetime import datetime


class Collection(Base):
    __tablename__ = "collections"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    project_id = Column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project = relationship(
        "Project", back_populates="collections", 
    )
    documents = relationship(
        "Document",
        back_populates="collection",
        cascade="all, delete-orphan",
    )
    webhook_url = Column(String, nullable=True)

    permissions = Column(
        JSONB,
        nullable=True,
        default=lambda: {
            "create": [],
            "read": [],
            "update": [],
            "delete": [],
        },
    )

    __table_args__ = (
        (
            Index(
                "idx_collection_project_id_name",
                "name",
                "project_id",
            )
        ),
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
    data = Column(JSONB, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    collection = relationship("Collection", back_populates="documents")

    __table_args__ = (
        Index(
            "ix_documents_data_gin",
            "data",
            postgresql_using="gin",
            postgresql_ops={"data": "jsonb_ops"},
        ),
    )
