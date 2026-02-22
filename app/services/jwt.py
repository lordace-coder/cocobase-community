from datetime import datetime, timedelta, timezone
import jwt
from jwt import PyJWTError, ExpiredSignatureError

from fastapi import status
from fastapi.exceptions import HTTPException

from app.core import config as settings
from app.models.app_client import AppUser


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(days=5))
    to_encode.update({"exp": expire})

    return jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return payload

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except PyJWTError:
        return None


def create_app_user_token(user: AppUser):
    to_encode = {
        "userId": user.id,
        "email": user.email,
        "exp": datetime.now(timezone.utc) + timedelta(days=2),
    }

    return jwt.encode(
        to_encode,
        user.client_id,
        algorithm=settings.ALGORITHM,
    )


def decode_app_user_token(token: str, projectId: str):
    try:
        payload = jwt.decode(
            token,
            projectId,
            algorithms=[settings.ALGORITHM],
        )
        return payload

    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )

    except PyJWTError:
        return None


def generate_reset_token(email: str):
    payload = {
        "sub": str(email),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=10),
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def verify_reset_token(token: str):
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        email: str | None = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token")

        return email

    except PyJWTError:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired token",
        )
