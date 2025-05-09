from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.app_client import Project,AppUser
from app.schemas.projects import ProjectInDBBase,ProjectCreate

router = APIRouter(prefix='/project' ,dependencies=[Depends(get_current_user)])


@router.get("/")
def GetAllProjects(user:User=Depends(get_current_user),db:Session= Depends(get_db))->ProjectInDBBase:
    projects = db.query(Project).filter(Project.user_id == user.id)
    return projects


@router.post("/")
def CreateNewProject(payload:ProjectCreate,user:User=Depends(get_current_user),db:Session= Depends(get_db))->ProjectInDBBase:
    pass