from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, get_project_with_access
from app.models.user import User
from app.models.app_client import Project
from app.models.orm_api_keys import ORMApiKey
from app.schemas.orm_api_keys import (
    ORMApiKeyCreate,
    ORMApiKeyCreateResponse,
    ORMApiKeyResponse,
    ORMApiKeyUpdate,
)
from app.services.utils import generate_orm_api_key

router = APIRouter(
    prefix="/project/{project_id}/orm-keys",
    tags=["ORM API Keys"],
)


@router.post("/", status_code=201, response_model=ORMApiKeyCreateResponse)
def create_orm_api_key(
    project_id: str,
    payload: ORMApiKeyCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Create a new ORM API key for a project.

    The API key will be in the format: coco_orm_<project_id>_<random_32_chars>

    **Warning:** The full API key is only shown once during creation. Save it securely!
    """
    # Verify project access
    project = get_project_with_access(project_id, user, db)

    # Generate the API key
    api_key = generate_orm_api_key(project_id)

    # Calculate expiry date if provided
    expires_at = None
    if payload.expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=payload.expires_in_days)

    # Create the ORM API key record
    orm_key = ORMApiKey(
        project_id=project.id,
        name=payload.name,
        permissions=payload.permissions,
        expires_at=expires_at,
        created_by=user.id,
        rate_limit=payload.rate_limit,
    )

    # Hash the key and store the prefix
    orm_key.set_key(api_key)

    db.add(orm_key)
    db.commit()
    db.refresh(orm_key)

    # Return response with the full key (only time it will be shown)
    return ORMApiKeyCreateResponse(
        id=orm_key.id,
        project_id=orm_key.project_id,
        name=orm_key.name,
        key=api_key,  # Full key shown only on creation
        key_prefix=orm_key.key_prefix,
        permissions=orm_key.permissions,
        created_at=orm_key.created_at,
        expires_at=orm_key.expires_at,
        is_active=orm_key.is_active,
        rate_limit=orm_key.rate_limit,
    )


@router.get("/", response_model=list[ORMApiKeyResponse])
def list_orm_api_keys(
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    active_only: bool = Query(False, description="Filter to show only active keys"),
):
    """
    List all ORM API keys for a project.

    Returns metadata about the keys (without the actual key values).
    """
    # Verify project access
    project = get_project_with_access(project_id, user, db)

    # Build query
    query = db.query(ORMApiKey).filter(ORMApiKey.project_id == project.id)

    if active_only:
        query = query.filter(ORMApiKey.is_active == True)

    # Order by creation date (newest first)
    orm_keys = query.order_by(ORMApiKey.created_at.desc()).all()

    return orm_keys


@router.get("/{key_id}", response_model=ORMApiKeyResponse)
def get_orm_api_key(
    project_id: str,
    key_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Get details of a specific ORM API key.

    Returns metadata about the key (without the actual key value).
    """
    # Verify project access
    project = get_project_with_access(project_id, user, db)

    # Get the key
    orm_key = (
        db.query(ORMApiKey)
        .filter(ORMApiKey.id == key_id, ORMApiKey.project_id == project.id)
        .first()
    )

    if not orm_key:
        raise HTTPException(404, "ORM API key not found")

    return orm_key


@router.patch("/{key_id}", response_model=ORMApiKeyResponse)
def update_orm_api_key(
    project_id: str,
    key_id: str,
    payload: ORMApiKeyUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Update an ORM API key's metadata.

    You can update the name, permissions, active status, and rate limit.
    """
    # Verify project access
    project = get_project_with_access(project_id, user, db)

    # Get the key
    orm_key = (
        db.query(ORMApiKey)
        .filter(ORMApiKey.id == key_id, ORMApiKey.project_id == project.id)
        .first()
    )

    if not orm_key:
        raise HTTPException(404, "ORM API key not found")

    # Update only provided fields
    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(orm_key, key, value)

    db.add(orm_key)
    db.commit()
    db.refresh(orm_key)

    return orm_key


@router.delete("/{key_id}")
def delete_orm_api_key(
    project_id: str,
    key_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Delete an ORM API key.

    This action is permanent and will immediately revoke access for the key.
    """
    # Verify project access
    project = get_project_with_access(project_id, user, db)

    # Delete the key
    result = (
        db.query(ORMApiKey)
        .filter(ORMApiKey.id == key_id, ORMApiKey.project_id == project.id)
        .delete(synchronize_session=False)
    )

    if not result:
        raise HTTPException(404, "ORM API key not found")

    db.commit()
    return {"message": "ORM API key deleted successfully"}


@router.post("/{key_id}/deactivate", response_model=ORMApiKeyResponse)
def deactivate_orm_api_key(
    project_id: str,
    key_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Deactivate an ORM API key without deleting it.

    This is useful for temporarily revoking access while keeping the key record.
    """
    # Verify project access
    project = get_project_with_access(project_id, user, db)

    # Get the key
    orm_key = (
        db.query(ORMApiKey)
        .filter(ORMApiKey.id == key_id, ORMApiKey.project_id == project.id)
        .first()
    )

    if not orm_key:
        raise HTTPException(404, "ORM API key not found")

    orm_key.is_active = False
    db.add(orm_key)
    db.commit()
    db.refresh(orm_key)

    return orm_key


@router.post("/{key_id}/activate", response_model=ORMApiKeyResponse)
def activate_orm_api_key(
    project_id: str,
    key_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Reactivate a deactivated ORM API key.
    """
    # Verify project access
    project = get_project_with_access(project_id, user, db)

    # Get the key
    orm_key = (
        db.query(ORMApiKey)
        .filter(ORMApiKey.id == key_id, ORMApiKey.project_id == project.id)
        .first()
    )

    if not orm_key:
        raise HTTPException(404, "ORM API key not found")

    # Check if key is expired
    if orm_key.expires_at and orm_key.expires_at < datetime.utcnow():
        raise HTTPException(400, "Cannot activate an expired key")

    orm_key.is_active = True
    db.add(orm_key)
    db.commit()
    db.refresh(orm_key)

    return orm_key
