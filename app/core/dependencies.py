from fastapi import Depends, HTTPException, Header, status, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.app_client import Project
from app.models.user import User
from app.services.jwt import decode_access_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
):
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("userId")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Token missing userId"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return db.query(User).filter(User.id == user_id).first()


def get_project(
    x_api_key: str = Header(...), db: Session = Depends(get_db)
) -> tuple[Project, User]:
    if not x_api_key:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Missing the authorization header [x-api-key] ,Contact the developer or check out the documentation",
        )
    project = db.query(Project).filter(Project.api_key == x_api_key).first()

    if not project:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Invalid x-api-key passed in, no project with the given key was found",
        )
    # todo check if this domain is included in the projects allowed domains
    return project, project.owner
