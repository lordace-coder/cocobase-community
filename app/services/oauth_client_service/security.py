# app/core/security.py
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext

from app.core.config import SECRET_KEY

# Configuration - move to settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 30
AUTH_CODE_EXPIRE_MINUTES = 10

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_token(length: int = 32) -> str:
    """Generate a secure random token"""
    return secrets.token_urlsafe(length)


def hash_secret(secret: str) -> str:
    """Hash client secret or password"""
    return pwd_context.hash(secret)


def verify_secret(plain_secret: str, hashed_secret: str) -> bool:
    """Verify a secret against its hash"""
    return pwd_context.verify(plain_secret, hashed_secret)


def create_jwt_token(
    data: dict,
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_jwt_token(token: str) -> dict:
    """Decode and verify a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token has expired")
    except jwt.JWTError:
        raise ValueError("Invalid token")


def create_id_token(user_data: dict, client_id: str, nonce: Optional[str] = None) -> str:
    """Create an OpenID Connect ID token"""
    now = datetime.utcnow()
    
    payload = {
        "iss": "https://cocobase.com",  # Your issuer URL
        "sub": user_data["id"],
        "aud": client_id,
        "exp": now + timedelta(hours=1),
        "iat": now,
        "email": user_data.get("email"),
        "email_verified": user_data.get("email_verified", False),
        "name": user_data.get("name"),
        "picture": user_data.get("picture"),
    }
    
    if nonce:
        payload["nonce"] = nonce
    
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def generate_pkce_challenge(verifier: str) -> str:
    """Generate PKCE code challenge from verifier"""
    digest = hashlib.sha256(verifier.encode()).digest()
    import base64
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return challenge


def verify_pkce_challenge(verifier: str, challenge: str) -> bool:
    """Verify PKCE code verifier against challenge"""
    expected_challenge = generate_pkce_challenge(verifier)
    return secrets.compare_digest(expected_challenge, challenge)