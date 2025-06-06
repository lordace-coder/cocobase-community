from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.core.dependencies import get_project
from app.models.app_client import Project
from app.models.user import User
from app.models.app_client import AppUser

router = APIRouter(prefix="/auth-collections", tags=["App Client"])


class AppUserSchema(BaseModel):
    email: str
    password: str
    data: Optional[dict] = None


@router.post("/login")
def user_login(
    payload: AppUserSchema,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
):
    project = proj[0]
    try:
        user = (
            db.query(AppUser)
            .filter(AppUser.client_id == project.id, AppUser.email == payload.email)
            .first()
        )
        if not user:
            raise HTTPException(404, "Account with this email does not exist")
        # check if password is valid
        if user.compare_password(payload.password):
            # return api token
            return {"access_key": "some-api-key"}
        else:
            raise HTTPException(400, "Invalid password value")

    except Exception as err:
        raise HTTPException(400, "An error occured " + str(err))


@router.post("/signup")
def create_new_user(
    payload: AppUserSchema,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
):
    project = proj[0]
    if (
        db.query(AppUser)
        .filter(AppUser.client_id == project.id, AppUser.email == payload.email)
        .first()
    ):
        raise HTTPException(400, "User with this email lready exists")
    else:
        # create new user
        user = AppUser(**payload.model_dump())
        user.set_password(payload.password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"access_token": "some token"}


# list users
@router.get("/users")
def list_all_users(
    db: Session = Depends(get_db), proj: tuple[Project, User] = Depends(get_project)
) -> list[AppUserSchema]:
    users = db.query(AppUser).filter(AppUser.client_id == proj[0].id)
    return users


# get user by id
@router.get("users/{id}")
def get_all_users(
    id: str,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
) -> AppUserSchema:
    users = (
        db.query(AppUser)
        .filter(AppUser.client_id == proj[0].id, AppUser.id == id)
        .first()
    )
    return users
