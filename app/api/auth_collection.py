from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.core.dependencies import get_app_user, get_project
from app.models.app_client import Project
from app.models.user import User
from app.models.app_client import AppUser
from app.services.google_login_helper import generate_oauth_url
from app.services.jwt import create_app_user_token, decode_app_user_token
from authlib.integrations.httpx_client import AsyncOAuth2Client

from app.services.oauth2_helper import TOKEN_ENDPOINT, USERINFO_ENDPOINT


router = APIRouter(prefix="/auth-collections", tags=["App Client"])


class AppUserSchema(BaseModel):
    email: str
    password: str
    data: Optional[dict] = None
    roles: Optional[list[str]] = []


class AppUserUpdateSchema(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    data: Optional[dict] = None


class AppUserResponse(BaseModel):
    email: str
    data: Optional[dict] = None
    client_id: str
    created_at: datetime
    id: str
    roles: Optional[list[str]] = []


class AppTokenResponse(BaseModel):
    access_token: str


@router.post("/login")
def user_login(
    payload: AppUserSchema,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
) -> AppTokenResponse:
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
            return {"access_token": create_app_user_token(user)}
        else:
            raise HTTPException(400, "Invalid password value")

    except Exception as err:
        raise HTTPException(400, "An error occured " + str(err))


@router.post("/signup")
def create_new_user(
    payload: AppUserSchema,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
) -> AppTokenResponse:
    project = proj[0]
    if (
        db.query(AppUser)
        .filter(AppUser.client_id == project.id, AppUser.email == payload.email)
        .first()
    ):
        raise HTTPException(400, "User with this email already exists")
    else:
        # create new user
        user = AppUser(**payload.model_dump())
        user.set_password(payload.password)
        user.client_id = project.id
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"access_token": create_app_user_token(user)}


# list users
@router.get("/users")
def list_all_users(
    db: Session = Depends(get_db), proj: tuple[Project, User] = Depends(get_project)
) -> list[AppUserResponse]:
    users = db.query(AppUser).filter(AppUser.client_id == proj[0].id)
    return users


# get user by id
@router.get("/users/{id}")
def get_all_users(
    id: str,
    db: Session = Depends(get_db),
    proj: tuple[Project, User] = Depends(get_project),
) -> AppUserResponse:
    users = (
        db.query(AppUser)
        .filter(AppUser.client_id == proj[0].id, AppUser.id == id)
        .first()
    )
    return users


# get current user
@router.get("/user")
def get_current_user_details(user: AppUser = Depends(get_app_user)) -> AppUserResponse:
    return user


# update user data
@router.patch("/user", response_model=AppUserResponse)
def update_current_user_details(
    payload: AppUserUpdateSchema,
    db: Session = Depends(get_db),
    user: AppUser = Depends(get_app_user),
) -> AppUserResponse:
    # Update only the fields that are set in the payload
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(user, field, value)

    if payload.password:
        user.set_password(payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


# *GOOGLE AUTHENTICATION LOGICS
@router.get("/login-google")
def login_with_google(
    proj: tuple[Project, User] = Depends(get_project),
):
    project = proj[0]

    # get required settings from project config
    config = dict(project.configs)
    GOOGLE_CLIENT_ID = config.get("GOOGLE_CLIENT_ID")
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            400, "You need to add GOOGLE_CLIENT_ID key to your project config"
        )

    redirect_url = config.get("GOOGLE_REDIRECT_URL")
    if not redirect_url:
        raise HTTPException(
            400, "You need to set the GOOGLE_REDIRECT_URL key in your project config"
        )
    url = generate_oauth_url(
        GOOGLE_CLIENT_ID=GOOGLE_CLIENT_ID, redirect_url=redirect_url
    )
    return {"url": url}


@router.get("/auth-google-redirect/{project_id}")
async def auth(code: str, project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).get(project_id)

    # GET PROJECT CONFIG FIRST
    config = dict(project.configs)

    GOOGLE_CLIENT_ID = config.get("GOOGLE_CLIENT_ID")
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(
            400, "You need to add GOOGLE_CLIENT_ID key to your project config"
        )

    # GET REDIRECT URL
    redirect_url = config.get("GOOGLE_REDIRECT_URL")
    if not redirect_url:
        raise HTTPException(
            400, "You need to set the GOOGLE_REDIRECT_URL key in your project config"
        )

    # GET CLIENT SECRET
    GOOGLE_CLIENT_SECRET = config.get("GOOGLE_CLIENT_SECRET")
    if not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            400, "You need to configure GOOGLE_CLIENT_SECRET key for your project"
        )

    GOOGLE_COMPLETE_URL = config.get("GOOGLE_COMPLETE_URL")
    if not GOOGLE_COMPLETE_URL:
        raise HTTPException(
            400, "You need to add GOOGLE_COMPLETE_URL key to your project "
        )

    try:
        async with AsyncOAuth2Client(
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
        ) as client:
            # Fetch token from Google
            try:
                token = await client.fetch_token(
                    TOKEN_ENDPOINT,
                    code=code,
                    redirect_uri=redirect_url,
                )
            except Exception as e:
                print(f"Token fetch error: {e}")
                built_url = f"{GOOGLE_COMPLETE_URL}?error=invalid_authorization_code"
                return RedirectResponse(built_url)

            # Get user info from Google
            try:
                headers = {"Authorization": f"Bearer {token['access_token']}"}
                userinfo = await client.get(USERINFO_ENDPOINT, headers=headers)
                user = userinfo.json()
            except Exception as e:
                print(f"User info fetch error: {e}")
                built_url = f"{GOOGLE_COMPLETE_URL}?error=failed_to_get_user_info"
                return RedirectResponse(built_url)

            # Validate email
            email: str | None = user.get("email")
            if not email:
                built_url = f"{GOOGLE_COMPLETE_URL}?error=no_email_provided"
                return RedirectResponse(built_url)

            # Check if user exists
            try:
                existing_user = db.query(AppUser).filter(AppUser.email == email,AppUser.client_id== project_id).first()

                if existing_user:
                    # User exists - check if they used OAuth before
                    if not existing_user.oauth_id:
                        built_url = f"{GOOGLE_COMPLETE_URL}?error=email_already_registered_with_password"
                        return RedirectResponse(built_url)

                    # User exists and used OAuth - log them in
                    access_token = create_app_user_token(existing_user)

                    built_url = f"{GOOGLE_COMPLETE_URL}?coco-super-token={access_token}"
                    return RedirectResponse(built_url)

                else:
                    # Create new user
                    new_user = AppUser(
                        email=email,
                        client_id=project.id,
                        oauth_id=user.get("sub"),
                        password=email,
                        data={
                            "username": str(user.get("name", "")).replace(" ", "")
                            or f"user_{user.get('sub', '')[:8]}"
                        },
                    )
                    db.add(new_user)
                    db.commit()

                    # Generate token for new user
                    access_token = create_app_user_token()
                    built_url = f"{GOOGLE_COMPLETE_URL}?coco-super-token={access_token}"
                    print(f"New user created: {built_url}")
                    return RedirectResponse(built_url)

            except Exception as e:
                print(f"Database error: {e}")
                db.rollback()
                built_url = f"{GOOGLE_COMPLETE_URL}?error=database_error"
                return RedirectResponse(built_url)

    except Exception as e:
        print(f"Unexpected error in Google auth: {e}")
        built_url = f"{GOOGLE_COMPLETE_URL}?error=authentication_failed"
        return RedirectResponse(built_url)
