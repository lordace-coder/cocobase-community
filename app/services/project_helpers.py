# Simple service functions
from app.models.app_client import Project
from app.models.user import User


def share_project_with_user(
    project_id: str, owner_id: str, target_user_email: str, db_session
):
    """Share a project with another user by email"""
    project = (
        db_session.query(Project)
        .filter(Project.id == project_id, Project.user_id == owner_id)
        .first()
    )
    if not project:
        raise ValueError("Project not found or you don't own it")

    target_user = db_session.query(User).filter(User.email == target_user_email).first()
    if not target_user:
        raise ValueError("User not found")

    if target_user not in project.shared_with:
        project.shared_with.append(target_user)
        db_session.commit()
    return project


def get_user_projects(user_id: str, db_session):
    """Get all projects a user owns or has access to"""
    user = db_session.query(User).get(user_id)
    return {"owned": user.projects, "shared": user.shared_projects}
