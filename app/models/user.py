from sqlalchemy import UUID, Column, Integer, String, DateTime
from app.core.database import Base
from datetime import datetime
import uuid
from uuid import uuid4
from sqlalchemy.orm import relationship

from app.services.utils import hash_password, verify_password

# This function generates a password that is unusable for authentication purposes.
# It uses a UUID to ensure uniqueness and prepends it with a specific string.
# This is useful for marking users who are not allowed to log in or have been deactivated.

def generate_unusable_password():
    return f"!UNUSABLE-{uuid4()}"


class User(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    username = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String,)
    full_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    google_id = Column(String, unique=True, nullable=True)

    projects = relationship("Project", back_populates="owner", cascade="all, delete-orphan")

    def set_password(self, password: str) -> None:
        self.password = hash_password(password)

    def compare_password(self, password: str) -> bool:
        return verify_password(password, self.password)
