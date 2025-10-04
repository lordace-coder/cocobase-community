from datetime import datetime, timedelta
from jose import JWTError, jwt, ExpiredSignatureError
from fastapi.exceptions import HTTPException
from fastapi import status
from app.core import config as settings
from app.models.app_client import AppUser, Project


def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(days=5))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str):
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        return None


def create_app_user_token(user: AppUser):
    to_encode = {"userId": user.id, "email": user.email}
    expire = datetime.utcnow() + (timedelta(days=2))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, user.client_id, algorithm=settings.ALGORITHM)


def decode_app_user_token(token, projectId):
    try:
        payload = jwt.decode(token, projectId, algorithms=[settings.ALGORITHM])
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        return None




def generate_reset_token(email: int):
    expire = datetime.utcnow() + timedelta(minutes=10)
    payload = {"sub": str(email), "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_reset_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=400, detail="Invalid token")
        return email
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
