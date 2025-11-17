from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    Request,
    Body,
    Response,
)
from pydantic import BaseModel, Field
from sqlalchemy import or_, func
from sqlalchemy.orm import Session, joinedload
from app.models.notifications import Notification
from app.schemas.auth_collection import (
    AppUserSchema,
    AppUserResponse,
    AppUserUpdateSchema,
)
from app.core.database import get_db
from app.core.dependencies import (
    get_current_user,
    get_project_with_access,
    verify_project_access,
)
from app.core.middleware import track_api_call
from app.models.collections import Collection, Document
from app.models.pricing import get_current_plan
from app.models.user import User
from app.models.app_client import Project, AppUser
from app.schemas.collections import (
    CollectionCreateSchema,
    CollectionPermissionsRequest,
    CollectionSchema,
    DocumentCreateSchema,
    PaginatedResponse,
)
from app.schemas.notifications import NotificationSchema
from app.schemas.projects import ProjectInDBBase, ProjectCreate, ProjectUpdate
from app.schemas.collections import DocumentSchema
from app.schemas.user import TeamMemberSchema, UserSchema
from app.services.email import notify_limit_reached, notify_limit_warning
from app.services.utils import generate_api_key, handle_webhook_call
from app.core.config import DEFAULT_PERMISSION_DICT


router = APIRouter(
    prefix="/project",
    tags=["Project"],
)


# ============================================
# REQUEST SCHEMAS
# ============================================


class DeleteItemsRequest(BaseModel):
    """Schema for bulk delete operations."""

    ids: list[str] = Field(..., description="List of IDs to delete", min_length=1)

    model_config = {"json_schema_extra": {"example": {"ids": ["id1", "id2", "id3"]}}}


# ============================================
# HELPER FUNCTIONS (DRY Principle)
# ============================================


def get_collection_with_access(
    collection_id: str, project: Project, db: Session
) -> Collection:
    """Reusable function to get collection with validation."""
    collection = (
        db.query(Collection)
        .filter(Collection.id == collection_id, Collection.project_id == project.id)
        .first()
    )

    if not collection:
        raise HTTPException(404, "Collection not found")

    return collection


def ensure_collection_permissions(collection: Collection, db: Session) -> None:
    """Ensure collection has valid permissions dict."""
    if not collection.permissions or not isinstance(collection.permissions, dict):
        collection.permissions = DEFAULT_PERMISSION_DICT
        db.add(collection)
        db.commit()
        db.refresh(collection)


# ============================================
# PROJECT ROUTES
# ============================================


@router.get("/")
def get_all_projects(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ProjectInDBBase]:
    """Optimized: Single query with eager loading."""
    # Debug: measure query time to help diagnose slowness
    import time
    import logging

    logger = logging.getLogger(__name__)

    start = time.time()
    projects = (
        db.query(Project)
        .options(joinedload(Project.owner))  # Eager load owner
        .filter(or_(Project.user_id == user.id, Project.shared_with.any(id=user.id)))
        .all()
    )
    duration = (time.time() - start) * 1000
    logger.debug("get_all_projects executed in %.1fms for user %s", duration, user.id)
    return projects


@router.post("/")
def create_project(
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectInDBBase:
    """Optimized: Use exists() for faster check."""
    # Optimized existence check
    exists = db.query(
        db.query(Project)
        .filter(Project.name == payload.name, Project.owner == user)
        .exists()
    ).scalar()

    if exists:
        raise HTTPException(400, "Project with this name already exists")

    proj = Project(**payload.model_dump(), owner=user)
    proj.api_key = generate_api_key()
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


# NOTIFICATIONS
@router.get("/notifications")
def get_user_notifications( user: User = Depends(get_current_user),
    db: Session = Depends(get_db),)->list[NotificationSchema]:
    """Fetch user notifications."""
    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )
    return notifications
@router.delete("/{id}")
def delete_project(
    id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Optimized: Added error handling."""
    result = (
        db.query(Project)
        .filter(Project.id == id, Project.user_id == user.id)
        .delete(synchronize_session=False)
    )

    if not result:
        raise HTTPException(404, "Project not found or access denied")

    db.commit()
    return {"message": "Project deleted successfully"}


@router.get("/{id}")
def get_project(
    id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    """Optimized: Eager loading and cleaner code."""
    verify: tuple[Project, User, User] = verify_project_access(user, id, db)
    project, owner, current_user = verify

    # Build team members list
    team_members = [TeamMemberSchema(email=owner.email, role="admin")]
    team_members.extend(
        TeamMemberSchema(email=member.email, role="member")
        for member in project.shared_with
    )

    return {
        "id": project.id,
        "name": project.name,
        "user_id": project.user_id,
        "api_key": project.api_key,
        "created_at": project.created_at,
        "allowed_origins": project.allowed_origins,
        "callback_url": project.callback_url,
        "configs": project.configs,
        "owner": UserSchema.model_validate(owner),
        "shared_with": team_members,
    }


@router.get("/regen-api-key/{projectId}", response_model=ProjectInDBBase)
def generate_new_api_key(
    projectId: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Optimized: Added validation."""
    project = (
        db.query(Project)
        .filter(Project.id == projectId, Project.user_id == user.id)
        .first()
    )

    if not project:
        raise HTTPException(404, "Project not found or access denied")

    project.api_key = generate_api_key()
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.patch("/{id}")
def update_project(
    id: str,
    payload: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectInDBBase:
    """Optimized: Eager loading and cleaner response building."""
    project = (
        db.query(Project)
        .options(joinedload(Project.owner), joinedload(Project.shared_with))
        .filter(
            Project.id == id,
            or_(
                Project.user_id == user.id, Project.shared_with.any(User.id == user.id)
            ),
        )
        .first()
    )

    if not project:
        raise HTTPException(404, "Project not found or access denied")

    # Update only provided fields
    update_data = payload.dict(exclude_unset=True)
    for key, val in update_data.items():
        setattr(project, key, val)

    db.add(project)
    db.commit()
    db.refresh(project)

    owner = project.owner
    team_members = [TeamMemberSchema(email=owner.email, role="admin")]
    team_members.extend(
        TeamMemberSchema(email=member.email, role="member")
        for member in project.shared_with
    )

    return {
        "id": project.id,
        "name": project.name,
        "user_id": project.user_id,
        "api_key": project.api_key,
        "created_at": project.created_at,
        "allowed_origins": project.allowed_origins,
        "callback_url": project.callback_url,
        "configs": project.configs,
        "owner": UserSchema.model_validate(owner),
        "shared_with": team_members,
    }


# ============================================
# COLLECTION ROUTES
# ============================================


@router.post("/{id}/collection", status_code=201, response_model=CollectionSchema)
def create_collection(
    id: str,
    payload: CollectionCreateSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Optimized: Use helper function and exists() check."""
    project = get_project_with_access(id, user, db)

    # Optimized existence check
    exists = db.query(
        db.query(Collection)
        .filter(Collection.project_id == project.id, Collection.name == payload.name)
        .exists()
    ).scalar()

    if exists:
        raise HTTPException(400, "Collection with this name already exists")

    new_collection = Collection(
        **payload.model_dump(),
        project_id=project.id,
        project=project,
    )

    db.add(new_collection)
    db.commit()
    db.refresh(new_collection)
    return new_collection


@router.delete("/{id}/collection/{collection_id}")
def delete_collection(
    id: str,
    collection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Optimized: Use helper functions and better validation."""
    project = get_project_with_access(id, user, db)
    collection = get_collection_with_access(collection_id, project, db)

    db.delete(collection)
    db.commit()
    return {"message": "Collection deleted successfully"}


@router.get("/{id}/collections")
def get_collections_in_project(
    id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[CollectionSchema]:
    """Optimized: Eager load collections."""
    project = (
        db.query(Project)
        .options(joinedload(Project.collections))
        .filter(
            Project.id == id,
            or_(
                Project.user_id == user.id, Project.shared_with.any(User.id == user.id)
            ),
        )
        .first()
    )

    # Order collections by name (case-insensitive) if present
    if project and project.collections:
        project.collections.sort(key=lambda c: (c.name or "").lower())

    if not project:
        raise HTTPException(404, "Project not found")

    # Ensure all collections have permissions
    for collection in project.collections:
        ensure_collection_permissions(collection, db)

    return project.collections


@router.get("/{id}/collections/{collection_id}")
def get_collection_by_id(
    id: str,
    collection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CollectionSchema:
    """Optimized: Use helper functions. Cache removed to prevent stale data issues."""
    project = get_project_with_access(id, user, db)
    collection = get_collection_with_access(collection_id, project, db)
    ensure_collection_permissions(collection, db)

    return {
        "id": collection.id,
        "name": collection.name,
        "created_at": collection.created_at,
        "documents": collection.documents,
        "webhook_url": collection.webhook_url,
        "permissions": collection.permissions,
    }


# ============================================
# DOCUMENT ROUTES
# ============================================


@router.get(
    "/{id}/collections/{collection_id}/documents",
    response_model=PaginatedResponse[DocumentSchema],
)
# REMOVED @cache - Security issue! Each user should see their own data
def get_documents_in_collection(
    id: str,
    collection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """
    Optimized:
    - Removed cache (security issue - user-specific data)
    - Use helper functions
    - Single query for count
    - Eager load collection relationship
    - Convert to Pydantic for consistency
    """
    project = get_project_with_access(id, user, db)
    collection = get_collection_with_access(collection_id, project, db)

    # Single optimized count query
    total_docs = (
        db.query(func.count(Document.id))
        .filter(Document.collection_id == collection.id)
        .scalar()
    )

    # Optimized query with eager loading
    documents = (
        db.query(Document)
        .options(joinedload(Document.collection))
        .filter(Document.collection_id == collection.id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    # Convert to Pydantic for consistency
    document_schemas = [DocumentSchema.model_validate(doc) for doc in documents]

    return PaginatedResponse(
        total=total_docs,
        limit=limit,
        offset=offset,
        count=len(document_schemas),
        results=document_schemas,
    )


@router.post(
    "/{id}/collections/{collection_id}/documents", response_model=DocumentSchema
)
def create_document_in_collection(
    id: str,
    bg: BackgroundTasks,
    collection_id: str,
    payload: DocumentCreateSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentSchema:
    """Optimized: Use helper functions, eager load for webhook."""
    project = get_project_with_access(id, user, db)
    collection = get_collection_with_access(collection_id, project, db)

    document = Document(**payload.model_dump(), collection_id=collection.id)

    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.delete("/{id}/collections/{collection_id}/documents/{document_id}")
def delete_document_in_collection(
    id: str,
    collection_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Optimized: Use helper functions."""
    project = get_project_with_access(id, user, db)
    collection = get_collection_with_access(collection_id, project, db)

    result = (
        db.query(Document)
        .filter(
            Document.id == document_id,
            Document.collection_id == collection.id,
        )
        .delete(synchronize_session=False)
    )

    if not result:
        raise HTTPException(404, "Document not found")

    db.commit()
    return {"message": "Document deleted successfully"}


@router.delete("/{id}/collections/{collection_id}/documents")
def delete_multiple_documents_in_collection(
    id: str,
    collection_id: str,
    payload: DeleteItemsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Bulk delete multiple documents from a collection.

    Provide a list of document IDs in the request body to delete them all at once.
    """
    project = get_project_with_access(id, user, db)
    collection = get_collection_with_access(collection_id, project, db)

    result = (
        db.query(Document)
        .filter(
            Document.id.in_(payload.ids),
            Document.collection_id == collection.id,
        )
        .delete(synchronize_session=False)
    )

    if result == 0:
        raise HTTPException(404, "No documents found to delete")

    db.commit()
    return {"message": f"Deleted {result} documents successfully"}


@router.patch("/{id}/collections/{collection_id}/documents/{document_id}")
def update_document_in_collection(
    id: str,
    collection_id: str,
    document_id: str,
    bg: BackgroundTasks,
    payload: DocumentCreateSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> DocumentSchema:
    """Optimized: Use helper functions, better data handling."""
    project = get_project_with_access(id, user, db)
    collection = get_collection_with_access(collection_id, project, db)

    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.collection_id == collection.id)
        .first()
    )

    if not document:
        raise HTTPException(404, "Document not found")

    if not payload.data:
        raise HTTPException(400, "No data provided to update")

    # Merge data safely
    _data = dict(document.data) if document.data else {}
    _data.update(payload.data)
    document.data = _data

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


# ============================================
# APP USER ROUTES
# ============================================


@router.get("/{id}/users", response_model=PaginatedResponse[AppUserResponse])
def list_users(
    id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Optimized: Use helper function and optimized count."""
    project = get_project_with_access(id, user, db)

    # Optimized count
    total_users = (
        db.query(func.count(AppUser.id))
        .filter(AppUser.client_id == project.id)
        .scalar()
    )

    users = (
        db.query(AppUser)
        .filter(AppUser.client_id == project.id)
        .order_by(AppUser.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(
        total=total_users,
        limit=limit,
        offset=offset,
        count=len(users),
        results=users,
    )


@router.put("/{id}/users/{userid}")
def update_user(
    id: str,
    userid: str,
    payload: AppUserUpdateSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AppUserResponse:
    """Optimized: Use helper function."""
    project = get_project_with_access(id, user, db)

    app_user = (
        db.query(AppUser)
        .filter(AppUser.id == userid, AppUser.client_id == project.id)
        .first()
    )

    if not app_user:
        raise HTTPException(404, "App user not found")

    update_data = payload.model_dump(exclude_unset=True)

    for key, val in update_data.items():
        if key != "password":  # Handle password separately
            setattr(app_user, key, val)

    if payload.password:
        app_user.set_password(payload.password)

    db.add(app_user)
    db.commit()
    db.refresh(app_user)
    return app_user


@router.post("/{id}/users", status_code=201)
def create_user(
    id: str,
    bg: BackgroundTasks,
    payload: AppUserSchema,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AppUserResponse:
    """Optimized: Use helper function and exists() check."""
    project = get_project_with_access(id, user, db)
    plan = get_current_plan(project, db)

    # Check if user limit has been reached
    # max_users = 0 or None means unlimited users
    if plan.max_users is not None and plan.max_users > 0:
        current_user_count = (
            db.query(func.count(AppUser.id))
            .filter(AppUser.client_id == project.id)
            .scalar()
        )

        # Hard limit - deactivate project
        if current_user_count >= plan.max_users:
            project.is_active = False
            db.commit()

            # Notify user in background
            bg.add_task(notify_limit_reached, user, project, "users", plan.max_users)

            raise HTTPException(
                status_code=403,
                detail=f"User limit reached ({plan.max_users}). Project has been deactivated. Please upgrade your plan.",
            )

        # Soft limit - warning at 80% and 90%
        usage_percentage = (current_user_count / plan.max_users) * 100

        if usage_percentage >= 90:
            bg.add_task(
                notify_limit_warning,
                user,
                project,
                "users",
                current_user_count,
                plan.max_users,
                "critical",  # 90%+ is critical
            )
        elif usage_percentage >= 80:
            bg.add_task(
                notify_limit_warning,
                user,
                project,
                "users",
                current_user_count,
                plan.max_users,
                "warning",  # 80-89% is warning
            )

    # Optimized existence check
    exists = db.query(
        db.query(AppUser)
        .filter(AppUser.client_id == project.id, AppUser.email == payload.email)
        .exists()
    ).scalar()

    if exists:
        raise HTTPException(400, "User with this email already exists")

    app_user = AppUser(**payload.model_dump(), client_id=project.id)
    app_user.set_password(payload.password)
    db.add(app_user)
    db.commit()
    db.refresh(app_user)

    return app_user


@router.get("/{id}/users/{userid}")
def get_user(
    id: str,
    userid: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AppUserResponse:
    """Optimized: Use helper function and fix return type."""
    project = get_project_with_access(id, user, db)

    app_user = (
        db.query(AppUser)
        .filter(AppUser.client_id == project.id, AppUser.id == userid)
        .first()
    )

    if not app_user:
        raise HTTPException(404, "User not found")

    return app_user


@router.delete("/{project_id}/users/{id}")
def delete_user(
    project_id: str,
    id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Optimized: Use helper function."""
    project = get_project_with_access(project_id, user, db)
    result = (
        db.query(AppUser)
        .filter(AppUser.id == id, AppUser.client_id == project.id)
        .delete(synchronize_session=False)
    )
    if not result:
        raise HTTPException(404, "App user not found")
    db.commit()
    return {"message": "User deleted successfully"}


@router.delete("/{project_id}/users")
def delete_multiple_users(
    project_id: str,
    payload: DeleteItemsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Bulk delete multiple app users from a project.

    Provide a list of user IDs in the request body to delete them all at once.
    """
    project = get_project_with_access(project_id, user, db)
    result = (
        db.query(AppUser)
        .filter(AppUser.id.in_(payload.ids), AppUser.client_id == project.id)
        .delete(synchronize_session=False)
    )
    if result == 0:
        raise HTTPException(404, "No app users found to delete")
    db.commit()
    return {"message": f"Deleted {result} users successfully"}


# ============================================
# COLLECTION PERMISSIONS & CONFIG
# ============================================


@router.post("/{id}/collections/{collection_id}/permissions")
def update_permissions(
    collection_id: str,
    id: str,
    payload: CollectionPermissionsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CollectionSchema:
    """Optimized: Use helper functions."""
    project = get_project_with_access(id, user, db)
    collection = get_collection_with_access(collection_id, project, db)

    collection.permissions = payload.model_dump()
    db.add(collection)
    db.commit()
    db.refresh(collection)
    return collection


@router.patch("/{project_id}/users/{id}")
def add_user_roles(
    project_id: str,
    id: str,
    payload: list[str],
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AppUserResponse:
    """Optimized: Use helper function."""
    project = get_project_with_access(project_id, user, db)

    app_user = (
        db.query(AppUser)
        .filter(AppUser.id == id, AppUser.client_id == project.id)
        .first()
    )

    if not app_user:
        raise HTTPException(404, "App user not found")

    app_user.roles = payload
    db.add(app_user)
    db.commit()
    db.refresh(app_user)
    return app_user


@router.post("/{project_id}/update-config")
def update_project_config(
    project_id: str,
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Optimized: Use helper function."""
    project = get_project_with_access(project_id, user, db)

    project.configs = payload
    db.add(project)
    db.commit()
    db.refresh(project)
    return project.configs


class CollectionUpdateRequest(BaseModel):
    name: str | None = None
    webhook_url: str | None = None
    permissions: CollectionPermissionsRequest | None = None
    model_config = {"from_attributes": True}


@router.get(
    "/{project_id}/collections/{collection_id}", description="Get collection configs"
)
def get_collection_configs(
    project_id: str,
    collection_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CollectionUpdateRequest:
    """Optimized: Use helper functions."""
    project = get_project_with_access(project_id, user, db)
    collection = get_collection_with_access(collection_id, project, db)

    return {
        "webhook_url": collection.webhook_url,
        "permissions": collection.permissions,
        "name": collection.name,
    }


@router.patch("/{project_id}/collections/{collection_id}")
def update_collection(
    project_id: str,
    collection_id: str,
    payload: CollectionUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Optimized: Use helper functions and better error handling."""
    project = get_project_with_access(project_id, user, db)
    collection = get_collection_with_access(collection_id, project, db)

    try:
        update_data = payload.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            if hasattr(collection, key):
                setattr(collection, key, value)

        db.add(collection)
        db.commit()
        db.refresh(collection)
        return collection

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to update collection: {str(e)}")



