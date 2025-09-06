from fastapi import Depends,APIRouter
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.app_client import Project
from app.schemas.user import UserSchema
from app.core.dependencies import get_current_user
from app.services.project_helpers import share_project_with_user, get_user_projects
from fastapi import HTTPException

router = APIRouter(prefix="/collaborations", tags=["collaborations"])




# add user to your project
@router.get("/{project_id}/team-members")
def add_team_member(
    email: str,
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
)->UserSchema:
    """
        pass in the optional email param to add a new user
    """
    project = None
    if email:
        try:
            project = share_project_with_user(project_id, user.id, email,db)
        except Exception as e:
            raise HTTPException(400, "Error occured adding user to your project " + str(e))
    members = project.shared_with if project != None else db.query(Project).filter(Project.id == project_id , Project.owner == user.id)
    return members

# remove team member
@router.delete("/{project_id}/team-members")
def remove_team_member(
    email: str,
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
)->UserSchema:
    """
        pass in the optional email param to remove a user
    """
    project = db.query(Project).filter(Project.id == project_id , Project.owner == user.id).first()
    if not project:
        raise HTTPException(404, "Project not found or you don't own it")
    target_user = db.query(User).filter(User.email == email).first()
    if not target_user:
        raise HTTPException(404, "User not found")
    if target_user in project.shared_with:
        project.shared_with.remove(target_user)
        db.commit()
    return project.shared_with