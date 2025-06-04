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
from app.schemas.projects import ProjectInDBBase, ProjectCreate, ProjectUpdate
from app.schemas.collections import DocumentSchema
from app.schemas.suggestions import SuggestionCreate, SuggestionSchema
from app.services.utils import generate_api_key

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
@router.post("/suggestions", response_model=SuggestionSchema, status_code=201)
def create_suggestion(
    payload: SuggestionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SuggestionSchema:
    """Create a new suggestion."""
    suggestion = Suggestion(**payload.model_dump())
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
