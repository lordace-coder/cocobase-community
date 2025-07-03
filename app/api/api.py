from datetime import date
import uuid
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.collections import Collection, Document
from app.models.hits import RouteHit
from app.models.user import User
from app.models.app_client import Project, AppUser
from app.models.timeline import Suggestion, SuggestionLike
from app.schemas.collections import CollectionSchema, DocumentCreateSchema
from app.schemas.files import UploadedFileSchema
from app.schemas.projects import ProjectInDBBase, ProjectCreate, ProjectUpdate
from app.schemas.collections import DocumentSchema
from app.schemas.suggestions import SuggestionCreate, SuggestionSchema
from app.services.cloudinary import delete_file
from app.services.utils import generate_api_key
from app.models.files import UploadedFile, UserStorage


router = APIRouter(tags=["API"], prefix="/api")


class ProjectData(BaseModel):
    users: int
    projects: int
    api_calls: int


@router.get("/")
def get_project_data(db: Session = Depends(get_db)) -> ProjectData:
    users = db.query(User).count()
    projects = db.query(Project).count()
    hit = db.query(RouteHit).filter(RouteHit.created == date.today()).first()
    return {"users": users, "projects": projects, "api_calls": hit.hits if hit else 0}


# Suggestions endpoints
@router.post(
    "/suggestions",
    response_model=SuggestionSchema,
    status_code=201,
)
def create_suggestion(
    payload: SuggestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuggestionSchema:
    """Create a new suggestion."""
    suggestion = Suggestion(
        **payload.model_dump(),
    )
    name = "Anonymous User"
    if current_user.full_name:
        name = current_user.full_name
    else:
        name = current_user.username
    suggestion.name = name
    db.add(suggestion)

    try:
        db.commit()
        db.refresh(suggestion)
        return suggestion
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to create suggestion: {str(e)}")


@router.get("/suggestions", response_model=list[SuggestionSchema])
def list_suggestions(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 10,
    current_user: User = Depends(get_current_user),
) -> list[SuggestionSchema]:
    """List all suggestions with their like counts."""  # Get suggestions with like counts and user's like status
    suggestions = (
        db.query(
            Suggestion,
            func.count(SuggestionLike.id).label("likes_count"),
            func.bool_or(SuggestionLike.user_id == current_user.id).label("has_liked"),
        )
        .outerjoin(SuggestionLike)
        .group_by(Suggestion.id)
        .order_by(Suggestion.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Convert to schema format with like counts and user's like status
    return [
        SuggestionSchema(
            id=suggestion.id,
            name=suggestion.name,
            description=suggestion.description,
            created_at=suggestion.created_at,
            likes_count=likes_count,
            has_liked=bool(has_liked),
        )
        for suggestion, likes_count, has_liked in suggestions
    ]


@router.post("/suggestions/{suggestion_id}/like", response_model=dict)
async def toggle_like_suggestion(
    suggestion_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """
    Toggle like status for a suggestion.
    Returns the updated like status and count.
    """
    # Validate suggestion ID format
    try:
        uuid.UUID(suggestion_id)
    except ValueError:
        raise HTTPException(400, "Invalid suggestion ID format")
    """Toggle like/unlike for a suggestion."""
    # Check if suggestion exists
    suggestion = db.query(Suggestion).filter(Suggestion.id == suggestion_id).first()
    if not suggestion:
        raise HTTPException(404, "Suggestion not found")

    # Check if user has already liked
    existing_like = (
        db.query(SuggestionLike)
        .filter(
            SuggestionLike.suggestion_id == suggestion_id,
            SuggestionLike.user_id == current_user.id,
        )
        .first()
    )

    try:
        if existing_like:
            # Unlike: Remove the like
            db.delete(existing_like)
            action = "unliked"
        else:
            # Like: Add new like
            new_like = SuggestionLike(
                suggestion_id=suggestion_id,
                user_id=current_user.id,
            )
            db.add(new_like)
            action = "liked"

        db.commit()

        # Get updated like count
        like_count = (
            db.query(func.count(SuggestionLike.id))
            .filter(SuggestionLike.suggestion_id == suggestion_id)
            .scalar()
        )

        return {
            "status": "success",
            "action": action,
            "suggestion_id": suggestion_id,
            "likes_count": like_count,
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Failed to {action} suggestion: {str(e)}")


to_mb = lambda x: round(x / (1024 * 1024), 3)
to_kb = lambda x: round(x / 1024, 5)


@router.get("/get-storage-data")
def get_storage_information(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    storage_info: UserStorage = (
        db.query(UserStorage).filter(UserStorage.user == current_user).first()
    )

    if not storage_info:
        return {}
    return {
        "used_storage": to_mb(storage_info.used_storage),
        "max_storage": to_mb(storage_info.max_storage),
    }


@router.get("/get-files")
def get_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[UploadedFileSchema]:
    my_files = db.query(UploadedFile).filter(UploadedFile.user == current_user)
    return my_files


class DeleteFilesRequest(BaseModel):
    public_ids: list[str]


@router.delete("/delete-files")
def delete_files(
    payload: DeleteFilesRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    public_ids = payload.public_ids

    if not public_ids:
        raise HTTPException(400, detail="No files specified for deletion")

    # Query files belonging to the user
    files_to_delete = (
        db.query(UploadedFile)
        .filter(UploadedFile.user_id == current_user.id)
        .filter(UploadedFile.public_id.in_(public_ids))
        .all()
    )

    if not files_to_delete:
        raise HTTPException(404, detail="No matching files found for deletion")

    # Delete from Cloudinary
    for file in files_to_delete:
        try:
            delete_file(
                file.public_id,
            )
        except Exception as e:
            raise HTTPException(500, detail=f"Cloudinary deletion error: {str(e)}")

    # Delete from DB
    for file in files_to_delete:
        db.delete(file)

    # Update used_storage
    total_freed = sum(f.size for f in files_to_delete)
    if current_user.storage:
        current_user.storage.used_storage -= total_freed

    db.commit()

    return {
        "deleted_count": len(files_to_delete),
        "freed_space_bytes": total_freed,
        "message": "Files deleted successfully",
    }
