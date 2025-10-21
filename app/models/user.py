from sqlalchemy import UUID, Column, Integer, String, DateTime, Boolean
from app.core.database import Base
from datetime import datetime
from uuid import uuid4
from sqlalchemy.orm import relationship
from app.services.utils import hash_password, verify_password
from app.models.app_client import project_shares


def generate_unusable_password():
    return f"!UNUSABLE-{uuid4()}"


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    username = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(
        String,
    )
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    google_id = Column(String, unique=True, nullable=True)
    projects = relationship(
        "Project", back_populates="owner", cascade="all, delete-orphan"
    )
    shared_projects = relationship(
        "Project", secondary=project_shares, back_populates="shared_with"
    )
    confirmed_email = Column(Boolean, default=False)

    liked_suggestions = relationship(
        "Suggestion",
        secondary="suggestion_likes",
        back_populates="liked_by_users",
    )
    is_staff = Column(Boolean, default=False)
    payments = relationship("Payment", back_populates="user")
    
    def set_password(self, password: str) -> None:
        self.password = hash_password(password)

    def compare_password(self, password: str) -> bool:
        return verify_password(password, self.password)

    def __str__(self):
        return self.username
