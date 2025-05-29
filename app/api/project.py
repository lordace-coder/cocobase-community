from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models.user import User
from app.models.app_client import Project, AppUser
from app.schemas.projects import ProjectInDBBase, ProjectCreate, ProjectUpdate
from app.services.utils import generate_api_key

router = APIRouter(
    prefix="/project", dependencies=[Depends(get_current_user)], tags=["Project"]
)


@router.get("/")
def get_all_projects(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ProjectInDBBase]:
    projects = db.query(Project).filter(Project.user_id == user.id)
    return projects


@router.post("/")
def create_project(
    payload: ProjectCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectInDBBase:
    # check if project name exists
    if (
        db.query(Project)
        .filter(Project.name == payload.name, Project.owner == user)
        .count()
    ):
        raise HTTPException(400, "Project with this name already exists")
    proj = Project(**payload.model_dump(), owner=user)
    proj.api_key = generate_api_key()
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


@router.delete("/{id}")
def delete_project(
    id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    try:
        db.query(Project).filter(Project.id == id, Project.user_id == user.id).delete()
        db.commit()
        return
    except Exception as e:
        raise HTTPException(400, "Error occured " + str(e))


@router.get("/{id}")
def get_project(
    id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
)->ProjectInDBBase:
    try:
        x = (
            db.query(Project)
            .filter(Project.id == id, Project.user_id == user.id)
            .first()
        )
        return x
    except Exception as e:
        raise HTTPException(400, "Error occured " + str(e))


@router.get("/regen-api-key/{projectId}", response_model=ProjectInDBBase)
def generate_new_api_key(
    projectId: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    project = (
        db.query(Project)
        .filter(Project.id == projectId, Project.user_id == user.id)
        .first()
    )
    project.api_key = generate_api_key()
    db.add(project)
    db.commit()
    return project


@router.patch("/{id}")
def update_project(
    id: str,
    payload: ProjectUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectInDBBase:
    project = (
        db.query(Project).filter(Project.id == id, Project.user_id == user.id).first()
    )
    update_data = payload.dict(exclude_unset=True)

    for key, val in update_data.items():
        setattr(project, key, val)

    db.add(project)
    db.commit()
    db.refresh(project)
    return project


# get collections in a project
@router.get("/{id}/collections")
def get_collections_in_project(
    id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[ProjectInDBBase]:
    project = (
        db.query(Project)
        .filter(Project.id == id, Project.user_id == user.id)
        .first()
    )
    if not project:
        raise HTTPException(404, "Project not found")
    
    return project.collections