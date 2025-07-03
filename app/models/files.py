from sqlalchemy import Column, String, Integer, ForeignKey, Enum, Float
from sqlalchemy.orm import relationship, declarative_base
from app.core.database import Base
import enum


class FileType(enum.Enum):
    image = "image"
    video = "video"
    other = "other"


class UserStorage(Base):
    __tablename__ = "user_storage"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True)
    used_storage = Column(Integer, default=0)  # in bytes
    max_storage = Column(Integer, default=10 * 1024 * 1024)  # 10MB

    user = relationship("User", back_populates="storage")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    url = Column(String, nullable=False)
    public_id = Column(String, nullable=False)
    format = Column(String)
    file_type = Column(Enum(FileType))
    size = Column(Integer, nullable=False)  # in bytes

    user = relationship("User", back_populates="files")
