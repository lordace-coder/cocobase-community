from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid

from app.core.database import Base


def uuid4():
    return str(uuid.uuid4())


# =========================
# OAUTH CLIENTS (APPS)
# =========================
class OAuthClient(Base):
    __tablename__ = "oauth_clients"

    id = Column(String, primary_key=True, default=uuid4)
    client_id = Column(String, unique=True, index=True, nullable=False)
    client_secret = Column(String, nullable=False)  # HASHED
    name = Column(String, nullable=False)
    description = Column(Text)

    owner_user_id = Column(String, ForeignKey("users.id"), nullable=False)

    redirect_uris = Column(JSON, nullable=False)
    scopes = Column(JSON, default=["openid", "email", "profile"])
    is_confidential = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship("User")


# =========================
# AUTHORIZATION CODES
# =========================
class OAuthAuthorizationCode(Base):
    __tablename__ = "oauth_authorization_codes"

    id = Column(String, primary_key=True, default=uuid4)
    code = Column(String, unique=True, index=True, nullable=False)

    client_id = Column(String, ForeignKey("oauth_clients.client_id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    redirect_uri = Column(String, nullable=False)
    scope = Column(String)

    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


# =========================
# ACCESS TOKENS
# =========================
class OAuthAccessToken(Base):
    __tablename__ = "oauth_access_tokens"

    id = Column(String, primary_key=True, default=uuid4)
    token = Column(String, unique=True, index=True, nullable=False)

    client_id = Column(String, ForeignKey("oauth_clients.client_id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    scope = Column(String)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


# =========================
# REFRESH TOKENS
# =========================
class OAuthRefreshToken(Base):
    __tablename__ = "oauth_refresh_tokens"

    id = Column(String, primary_key=True, default=uuid4)
    token = Column(String, unique=True, index=True, nullable=False)

    client_id = Column(String, ForeignKey("oauth_clients.client_id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False)
    rotated_from = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


# =========================
# USER CONSENTS
# =========================
class OAuthUserConsent(Base):
    __tablename__ = "oauth_user_consents"

    id = Column(String, primary_key=True, default=uuid4)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    client_id = Column(String, ForeignKey("oauth_clients.client_id"), nullable=False)

    scope = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User")

    __table_args__ = (
        Index("idx_user_client_consent", "user_id", "client_id", unique=True),
    )


# =========================
# AUTH SESSIONS (OPTIONAL)
# =========================
class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id = Column(String, primary_key=True, default=uuid4)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)

    ip_address = Column(String)
    user_agent = Column(String)

    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
