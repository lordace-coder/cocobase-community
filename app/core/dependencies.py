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


def check_origin_allowed(project: Project, request: Request) -> bool:
    """Check if the request origin is allowed for this project"""
    # If no origins are specified, allow all origins
    if not project.allowed_origins or len(project.allowed_origins) == 0:
        return True

    # Get the origin from the request headers
    origin = request.headers.get("origin") or request.headers.get("referer")
    print("request origin -", origin)
    # If no origin in request, you might want to allow or deny based on your security requirements
    if not origin:
        return True

    # Normalize origin (remove trailing slash, convert to lowercase)
    origin = origin.rstrip("/").lower()

    # Check if origin matches any allowed origin
    for allowed_origin in project.allowed_origins:
        allowed = allowed_origin.rstrip("/").lower()
        if origin == allowed or origin.startswith(allowed):
            return True

    return False


from functools import lru_cache
from typing import Optional
from fastapi import Request, Header, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload


# Alternative: More aggressive caching with full object caching
class ProjectCache:
    """Enhanced cache implementation with full object caching."""

    def __init__(self, maxsize=1000, ttl=3600):
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache = {}
        self._timestamps = {}

    def get(self, key: str) -> Optional[tuple[Project, User]]:
        """Get from cache with TTL check."""
        import time

        if key in self._cache:
            if time.time() - self._timestamps[key] < self.ttl:
                return self._cache[key]
            else:
                # Expired
                self.delete(key)
        return None

    def set(self, key: str, value: tuple[Project, User]):
        """Set cache with TTL tracking."""
        import time

        if len(self._cache) >= self.maxsize:
            # Simple LRU: remove oldest
            oldest = min(self._timestamps.items(), key=lambda x: x[1])
            self.delete(oldest[0])

        self._cache[key] = value
        self._timestamps[key] = time.time()

    def delete(self, key: str):
        """Remove from cache."""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)

    def clear(self):
        """Clear entire cache."""
        self._cache.clear()
        self._timestamps.clear()


# Initialize enhanced cache
enhanced_project_cache = ProjectCache(maxsize=1000, ttl=3600)


def get_project(
    request: Request, x_api_key: str = Header(...), db: Session = Depends(get_db)
) -> tuple[Project, User]:
    """Enhanced version with full object caching."""

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing the authorization header [x-api-key]",
        )

    # Try to get full objects from cache
    cached_result = enhanced_project_cache.get(x_api_key)
    if cached_result:
        project, user = cached_result
        if not check_origin_allowed(project, request):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Request origin not allowed for this project",
            )
        if not project.active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive Project, Upgrade to continue or contact support.",
            )
        return project, user

    # Cache miss - query database with eager loading
    project = (
        db.query(Project)
        .options(joinedload(Project.owner))
        .filter(Project.api_key == x_api_key)
        .first()
    )

    if not project.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive Project, Upgrade to continue or contact support.",
        )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid x-api-key passed in",
        )

    if not check_origin_allowed(project, request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request origin not allowed for this project",
        )

    user = project.owner

    # Cache full objects (detach from session first)
    db.expunge(project)
    db.expunge(user)
    enhanced_project_cache.set(x_api_key, (project, user))

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


# ! THIS IS WHERE ACCESS WILL BE VERIFIED, CHECK IF THE USER HAS ACCESS TO THE PROJECT, AND RESTRICT HIS ACTIONS IN THE FUTURE
def verify_project_access(current_user: User, project_id: str, db: Session):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    owner = project.owner
    if project.user_id != current_user.id:
        # Check if current_user is in shared_with
        shared_emails = [member.email for member in project.shared_with]
        if current_user.email not in shared_emails:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this project",
            )
    return project, owner, current_user
