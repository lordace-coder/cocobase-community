from fastapi import Depends, APIRouter
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.app_client import Project
from app.schemas.user import TeamMemberSchema, UserSchema
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
) -> list[TeamMemberSchema]:
    """
    pass in the optional email param to add a new user
    """
    project = None
    if email:
        try:
            project = share_project_with_user(project_id, user.id, email, db)
        except Exception as e:
            raise HTTPException(
                400, "Error occured adding user to your project " + str(e)
            )

    if not project:
        project = (
            db.query(Project)
            .filter(Project.id == project_id, Project.owner == user.id)
            .first()
        )
        if not project:
            raise HTTPException(404, "Project not found or you don't own it")

    members = [project.owner] + project.shared_with

    return [
        TeamMemberSchema(
            email=member.email,
            role="admin" if member.id == project.owner_id else "member",
        )
        for member in members
    ]


# remove team member
@router.delete("/{project_id}/team-members")
def remove_team_member(
    email: str,
    project_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TeamMemberSchema]:
    """
    pass in the optional email param to remove a user
    """
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner == user.id)
        .first()
    )
    if not project:
        raise HTTPException(404, "Project not found or you don't own it")

    target_user = db.query(User).filter(User.email == email).first()
    if not target_user:
        raise HTTPException(404, "User not found")

    if target_user in project.shared_with:
        project.shared_with.remove(target_user)
        db.commit()

    members = [project.owner] + project.shared_with

    return [
        TeamMemberSchema(
            email=member.email,
            role="admin" if member.id == project.owner_id else "member",
        )
        for member in members
    ]
