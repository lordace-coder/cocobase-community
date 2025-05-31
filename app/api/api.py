from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.collections import Collection, Document
from app.models.hits import RouteHit
from app.models.user import User
from app.models.app_client import Project, AppUser
from app.schemas.collections import CollectionSchema, DocumentCreateSchema
from app.schemas.projects import ProjectInDBBase, ProjectCreate, ProjectUpdate
from app.schemas.collections import DocumentSchema
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
    hit = db.query(RouteHit).filter(RouteHit.created==date.today()).first()
    return {"users": users, "projects": projects, "api_calls": hit.hits if hit else 0}
