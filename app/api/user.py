import os
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.user import UserSchema, UserCreateSchema
from app.models.user import User
from app.services.jwt import create_access_token
from app.services.oauth2_helper import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    TOKEN_ENDPOINT,
    USERINFO_ENDPOINT,
    oauth_url,
)
from authlib.integrations.httpx_client import AsyncOAuth2Client


router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")
frontend_url = "https://cocobase.buzz"


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreateSchema, db: Session = Depends(get_db)) -> UserSchema:
    # check if user exists
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Account with this email already exists.")
    # check if user exists
    user = User(**payload.dict())
    user.set_password(payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users")
def get_users(db: Session = Depends(get_db)) -> list[UserSchema]:
    return db.query(User).all()


@router.post("/login")
def handle_login(
    db: Session = Depends(get_db), data: OAuth2PasswordRequestForm = Depends()
):
    email = data.username
    if email:
        user = db.query(User).filter(User.email == email).first()
        if user == None:
            raise HTTPException(404, "No Matching account for this")
        if not user.compare_password(data.password):
            raise HTTPException(400, "Invalid password")
        else:
            access_token = create_access_token(
                data={"user": data.username, "userId": user.id.__str__()}
            )
            return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(404, "No Matching account for this")


@router.get("/current-user")
def get_user_details(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> UserSchema:
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# login with google


@router.get(
    "/login-google",
    description="Dont make api calls to this route, Navigate to it to start the login process",
)
async def login():
    return RedirectResponse(oauth_url)


@router.get("/auth-google")
async def auth(code: str, db: Session = Depends(get_db)):
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
                    redirect_uri=f"http://127.0.0.1:5000/auth/auth-google",
                )
            except Exception as e:
                print(f"Token fetch error: {e}")
                built_url = f"{frontend_url}/login?error=invalid_authorization_code"
                return RedirectResponse(built_url)

            # Get user info from Google
            try:
                headers = {"Authorization": f"Bearer {token['access_token']}"}
                userinfo = await client.get(USERINFO_ENDPOINT, headers=headers)
                user = userinfo.json()
            except Exception as e:
                print(f"User info fetch error: {e}")
                built_url = f"{frontend_url}/login?error=failed_to_get_user_info"
                return RedirectResponse(built_url)

            # Validate email
            email: str | None = user.get("email")
            if not email:
                built_url = f"{frontend_url}/login?error=no_email_provided"
                return RedirectResponse(built_url)

            # Check if user exists
            try:
                existing_user = db.query(User).filter(User.email == email).first()

                if existing_user:
                    # User exists - check if they used OAuth before
                    if not existing_user.google_id:
                        built_url = f"{frontend_url}/login?error=email_already_registered_with_password"
                        return RedirectResponse(built_url)

                    # User exists and used OAuth - log them in
                    access_token = create_access_token(
                        data={
                            "user": existing_user.username,
                            "userId": existing_user.id,
                        }
                    )
                    built_url = f"{frontend_url}/login?token={access_token}"
                    return RedirectResponse(built_url)

                else:
                    # Create new user
                    new_user = User(
                        email=email,
                        google_id=user.get("sub"),
                        username=str(user.get("name", "")).replace(" ", "")
                        or f"user_{user.get('sub', '')[:8]}",
                    )
                    db.add(new_user)
                    db.commit()
                    db.refresh(new_user)

                    # Generate token for new user
                    access_token = create_access_token(
                        data={"user": new_user.username, "userId": new_user.id}
                    )
                    built_url = f"{frontend_url}/login?token={access_token}"
                    print(f"New user created: {built_url}")
                    return RedirectResponse(built_url)

            except Exception as e:
                print(f"Database error: {e}")
                db.rollback()
                built_url = f"{frontend_url}/login?error=database_error"
                return RedirectResponse(built_url)

    except Exception as e:
        print(f"Unexpected error in Google auth: {e}")
        built_url = f"{frontend_url}/login?error=authentication_failed"
        return RedirectResponse(built_url)
