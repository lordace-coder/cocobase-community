from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.app_client import Project,AppUser
from app.schemas.projects import ProjectInDBBase,ProjectCreate
from app.services.utils import generate_api_key

router = APIRouter(prefix='/project' ,dependencies=[Depends(get_current_user)])


@router.get("/")
def get_all_projects(user:User=Depends(get_current_user),db:Session= Depends(get_db))->list[ProjectInDBBase]:
    projects = db.query(Project).filter(Project.user_id == user.id)
    return projects


@router.post("/")
def create_project(payload:ProjectCreate,user:User=Depends(get_current_user),db:Session= Depends(get_db))->ProjectInDBBase:
    # check if project name exists
    if db.query(Project).filter(Project.name == payload.name):
        raise HTTPException(400,"Project with this name already exists")
    proj = Project(**payload.model_dump(),owner= user)
    proj.api_key = generate_api_key()
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj
