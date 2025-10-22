import time
from fastapi import BackgroundTasks, Depends, HTTPException, Header, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.app_client import AppUser, Project
from app.models.user import User
from app.services.jwt import decode_access_token, decode_app_user_token
from app.services.project_tracking import check_and_increment_api_usage

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# OPTIMIZATION 1: Enhanced TTL Cache with better performance
class TTLCache:
    """Optimized in-memory cache with automatic cleanup."""

    def __init__(self, ttl=60, max_size=10000):
        self.ttl = ttl
        self.max_size = max_size
        self.cache = {}
        self.access_times = {}
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # Cleanup every 5 minutes

    def get(self, key):
        """Get with automatic cleanup."""
        self._maybe_cleanup()

        value, expires = self.cache.get(key, (None, 0))
        if time.time() < expires:
            self.access_times[key] = time.time()  # Track access for LRU
            return value

        # Expired - remove it
        if key in self.cache:
            del self.cache[key]
            del self.access_times[key]
        return None

    def set(self, key, value):
        """Set with size management."""
        # Evict if at max size (LRU)
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.access_times.items(), key=lambda x: x[1])[0]
            del self.cache[oldest_key]
            del self.access_times[oldest_key]

        self.cache[key] = (value, time.time() + self.ttl)
        self.access_times[key] = time.time()

    def _maybe_cleanup(self):
        """Periodic cleanup of expired entries."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return

        expired_keys = [k for k, (_, exp) in self.cache.items() if now >= exp]
        for k in expired_keys:
            del self.cache[k]
            self.access_times.pop(k, None)

        self._last_cleanup = now

    def clear(self):
        self.cache.clear()
        self.access_times.clear()


# OPTIMIZATION 2: Separate caches with appropriate TTLs
user_cache = TTLCache(ttl=300, max_size=5000)  # 5 min - users change rarely
project_cache = TTLCache(ttl=60, max_size=10000)  # 1 min - projects more dynamic
token_cache = TTLCache(ttl=600, max_size=10000)  # 10 min - decoded tokens


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    """Optimized user lookup with token caching."""

    # OPTIMIZATION: Cache decoded token payload to avoid JWT decoding
    payload = token_cache.get(token)
    if not payload:
        payload = decode_access_token(token)
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        token_cache.set(token, payload)

    user_id = payload.get("userId")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token missing userId"
        )

    # Try user cache
    user = user_cache.get(user_id)
    if user:
        # Reattach to session if needed
        if user not in db:
            user = db.merge(user, load=False)
        return user

    # Cache miss - query DB
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Cache the user object (will be detached)
    db.expunge(user)
    user_cache.set(user_id, user)

    # Return attached version
    return db.merge(user, load=False)


def check_origin_allowed(project: Project, request: Request) -> bool:
    """
    Optimized origin check with early exits.
    Check if the request origin is allowed for this project.
    """
    # Fast path: no restrictions
    if not project.allowed_origins or len(project.allowed_origins) == 0:
        return True

    # Get origin once
    origin = request.headers.get("origin") or request.headers.get("referer")

    # Fast path: no origin header (might want to adjust based on security needs)
    if not origin:
        return True

    # Normalize once
    origin_normalized = origin.rstrip("/").lower()

    # OPTIMIZATION: Use set for O(1) lookup if many origins
    if len(project.allowed_origins) > 10:
        allowed_set = {o.rstrip("/").lower() for o in project.allowed_origins}
        return origin_normalized in allowed_set or any(
            origin_normalized.startswith(o) for o in allowed_set
        )

    # For small lists, direct iteration is faster
    for allowed_origin in project.allowed_origins:
        allowed = allowed_origin.rstrip("/").lower()
        if origin_normalized == allowed or origin_normalized.startswith(allowed):
            return True

    return False


def get_project_with_access(project_id: str, user: User, db: Session) -> Project:
    """
    Optimized project access check.
    Single query with proper indexing assumptions.
    """
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            or_(
                Project.user_id == user.id, Project.shared_with.any(User.id == user.id)
            ),
        )
        .first()
    )

    if not project:
        raise HTTPException(404, "Project not found or access denied")

    return project


# OPTIMIZATION 3: Lightweight project data cache
class ProjectDataCache:
    """
    Cache project data (not SQLAlchemy objects) to avoid detached instance errors.
    Much lighter and faster than caching full ORM objects.
    """

    def __init__(self, maxsize=5000, ttl=60):
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache = {}
        self._timestamps = {}

    def get(self, key: str):
        """Get from cache with TTL check."""
        if key in self._cache:
            if time.time() - self._timestamps[key] < self.ttl:
                return self._cache[key]
            else:
                self.delete(key)
        return None

    def set(self, key: str, value: dict):
        """Set cache with LRU eviction."""
        if len(self._cache) >= self.maxsize:
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


# Initialize optimized cache
project_data_cache = ProjectDataCache(maxsize=5000, ttl=60)


def get_project(
    request: Request,
    bg: BackgroundTasks,
    x_api_key: str = Header(...),
    db: Session = Depends(get_db),
) -> tuple[Project, User]:
    """
    Heavily optimized version with data caching (not ORM objects).
    Used for x-api-key based access (external API calls).
    """

    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing the authorization header [x-api-key]",
        )

    # OPTIMIZATION: Try cache first (data dict, not ORM objects)
    cached_data = project_data_cache.get(x_api_key)
    if cached_data:
        # Reconstruct lightweight objects from cached data
        project = (
            db.query(Project).filter(Project.id == cached_data["project_id"]).first()
        )
        user = db.query(User).filter(User.id == cached_data["user_id"]).first()

        if project and user:
            # Fast path validations
            if not project.active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Inactive Project, Upgrade to continue or contact support.",
                )

            # Origin check (cached allowed_origins)
            if not check_origin_allowed(project, request):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Request origin not allowed for this project",
                )

            # Check and increment API usage
            check_and_increment_api_usage(project, db, bg, user)
            return project, user

    # Cache miss or stale - query with eager loading
    from sqlalchemy.orm import joinedload

    project = (
        db.query(Project)
        .options(joinedload(Project.owner))
        .filter(Project.api_key == x_api_key)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid x-api-key passed in",
        )

    if not project.active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive Project, Upgrade to continue or contact support.",
        )

    if not check_origin_allowed(project, request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Request origin not allowed for this project",
        )

    user = project.owner

    # Check and increment API usage
    check_and_increment_api_usage(project, db, bg, user)

    # OPTIMIZATION: Cache lightweight data (not full ORM objects)
    project_data_cache.set(
        x_api_key,
        {
            "project_id": project.id,
            "user_id": user.id,
            "active": project.active,
            "allowed_origins": project.allowed_origins,
        },
    )

    return project, user


def get_app_user(
    request: Request,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
):
    """Optimized app user lookup with early returns."""

    token = request.headers.get("Authorization")
    if not token:
        return None

    token = token.replace("Bearer ", "")

    # OPTIMIZATION: Cache decoded app user tokens
    cache_key = f"app_token:{token}:{proj[0].id}"
    payload = token_cache.get(cache_key)

    if not payload:
        payload = decode_app_user_token(token, proj[0].id)
        if payload is None:
            return None
        token_cache.set(cache_key, payload)

    user_id = payload.get("userId")
    if not user_id:
        return None

    # Try cache first
    app_user = user_cache.get(f"app_user:{user_id}")
    if app_user:
        if app_user not in db:
            app_user = db.merge(app_user, load=False)
        return app_user

    # Cache miss
    app_user = db.query(AppUser).filter(AppUser.id == user_id).first()
    if not app_user:
        return None

    # Cache for future
    db.expunge(app_user)
    user_cache.set(f"app_user:{user_id}", app_user)

    return db.merge(app_user, load=False)


def verify_project_access(current_user: User, project_id: str, db: Session):
    """
    Optimized project access verification for dashboard.
    Does NOT check API limits (dashboard operations don't count).
    """
    # OPTIMIZATION: Try cache first
    cache_key = f"project_access:{project_id}:{current_user.id}"
    cached_result = project_cache.get(cache_key)

    if cached_result:
        project_id, owner_id, has_access = cached_result
        if has_access:
            project = db.query(Project).filter(Project.id == project_id).first()
            owner = db.query(User).filter(User.id == owner_id).first()
            if project and owner:
                return project, owner, current_user

    # Cache miss - query
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    owner = project.owner
    has_access = False

    if project.user_id == current_user.id:
        has_access = True
    else:
        # OPTIMIZATION: Use set for O(1) lookup if many shared users
        shared_emails = {member.email for member in project.shared_with}
        if current_user.email in shared_emails:
            has_access = True

    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this project",
        )

    # Cache the result
    project_cache.set(cache_key, (project.id, owner.id, True))

    return project, owner, current_user


def require_dashboard_access(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Project:
    """
    Dependency for dashboard routes.
    Does NOT check API limits - dashboard operations are free.
    """
    project = get_project_with_access(project_id, user, db)
    return project


def require_api_access(
    project: tuple[Project, User] = Depends(get_project),
) -> tuple[Project, User]:
    """
    Dependency for external API routes (x-api-key based).
    API limit checking is already done in get_project().
    """
    return project
