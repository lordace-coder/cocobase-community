from sqlalchemy import Column, String, Boolean, DateTime, Integer
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from app.core.database import Base
import secrets


class TwoFactorCode(Base):
    """Store 2FA codes for email verification"""
    __tablename__ = 'two_factor_codes'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)
    code = Column(String(6), nullable=False)  # 6-digit code
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    @staticmethod
    def generate_code():
        """Generate a 6-digit code"""
        return f"{secrets.randbelow(1000000):06d}"

    def is_expired(self):
        """Check if code is expired"""
        return datetime.utcnow() > self.expires_at

    def is_valid(self):
        """Check if code is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired()


class TwoFactorSettings(Base):
    """Store 2FA settings per user"""
    __tablename__ = 'two_factor_settings'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), unique=True, nullable=False, index=True)
    project_id = Column(String(255), nullable=False, index=True)
    is_enabled = Column(Boolean, default=False)
    backup_email = Column(String(255), nullable=True)
    last_verified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
