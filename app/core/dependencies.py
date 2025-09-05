import time
from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.app_client import AppUser, Project
from app.models.user import User
from app.services.jwt import decode_access_token, decode_app_user_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# Simple in-memory cache with TTL for DB-backed dependencies
class TTLCache:
    def __init__(self, ttl=60):
        self.ttl = ttl
        self.cache = {}

    def get(self, key):
        value, expires = self.cache.get(key, (None, 0))
        if time.time() < expires:
            return value
        return None

    def set(self, key, value):
        self.cache[key] = (value, time.time() + self.ttl)

    def clear(self):
        self.cache.clear()


project_cache = TTLCache(ttl=60)
user_cache = TTLCache(ttl=60)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    cached_id = user_cache.get(token)
    if cached_id:
        user = db.query(User).filter(User.id == cached_id).first()
        if user:
            return user
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("userId")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token missing userId"
        )
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    user_cache.set(token, user_id)
    return user


def get_project(
    x_api_key: str = Header(...), db: Session = Depends(get_db)
) -> tuple[Project, User]:
    cached_ids = project_cache.get(x_api_key)
    if cached_ids:
        project = db.query(Project).filter(Project.id == cached_ids[0]).first()
        user = db.query(User).filter(User.id == cached_ids[1]).first()
        if project and user:
            return project, user
    if not x_api_key:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Missing the authorization header [x-api-key] ,Contact the developer or check out the documentation",
        )
    project = db.query(Project).filter(Project.api_key == x_api_key).first()
    if not project:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Invalid x-api-key passed in, no project with the given key was found",
        )
    user = project.owner
    project_cache.set(x_api_key, (project.id, user.id))
    return project, user


def get_app_user(
    request: Request,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
):

    token = request.headers.get("Authorization")
    
    if token == None:
        return
    token = token.replace("Bearer ", "")
    
    payload = decode_app_user_token(token, proj[0].id)
    if payload is None:
        return None
    user_id = payload.get("userId")
    if user_id is None:
        return None

    user = db.query(AppUser).filter(AppUser.id == user_id).first()
    if not user:
        return None

    return user
