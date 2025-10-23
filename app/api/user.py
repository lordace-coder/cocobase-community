import os
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.schemas.user import UserSchema, UserCreateSchema
from app.models.user import User
from app.services.email import send_email
from app.services.jwt import (
    create_access_token,
    generate_reset_token,
    verify_reset_token,
)
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
async def create_user(payload: UserCreateSchema, db: Session = Depends(get_db)):
    # check if user exists
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(400, "Account with this email already exists.")

    # create user
    user = User(**payload.dict())
    user.set_password(payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate verification token and send email
    token = generate_reset_token(user.email)
    frontend_base_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    verification_url = f"{frontend_base_url}/verify-email/{token}"

    # Send verification email
    await send_email(
        user.email,
        "Verify Your Email - Cocobase",
        "c106c91f-48bf-420d-82dc-aeb7fb5c08ff",
        {"verification_link": verification_url, "username": user.username},
    )

    # Create access token
    access_token = create_access_token(
        data={"user": user.username, "userId": user.id.__str__()}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "is_verified": user.confirmed_email,
        "message": "Account created successfully. Please check your email to verify your account.",
    }


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
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "is_verified": user.confirmed_email,
                "username": user.username,
                "email": user.email,
            }
    else:
        raise HTTPException(404, "No Matching account for this")


@router.get("/current-user")
def get_user_details(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> UserSchema:
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# LOGIN WITH GOOGLE
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
                    redirect_uri=f"https://cocobase.pxxl.click/auth/auth-google",
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
                    # Create new user (Google users are auto-verified)
                    new_user = User(
                        email=email,
                        google_id=user.get("sub"),
                        username=str(user.get("name", "")).replace(" ", "")
                        or f"user_{user.get('sub', '')[:8]}",
                        confirmed_email=True,  # Auto-verify Google users
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


# FORGOT PASSWORD FUNCTIONALITIES
@router.get("/reset-password/{email}")
async def handle_password_reset(email: str, db: Session = Depends(get_db)):
    # verify user exists
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User does not exist")

    # generate token and password update link
    token = generate_reset_token(email)

    # Build reset URL using environment variable for frontend base URL
    frontend_base_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    reset_url = f"{frontend_base_url}/forgot_password/{token}"

    await send_email(
        user.email,
        "Password Reset",
        "a1e531aa-a09e-4811-aa76-c7ca62643eb8",
        {"reset_link": reset_url, "username": user.username},
    )
    return {"msg": "Password reset email sent"}


class PasswordUpdateSchema(BaseModel):
    new_password: str
    token: str


@router.post("/update-password")
def update_user_password(payload: PasswordUpdateSchema, db: Session = Depends(get_db)):
    # confirm token
    email = verify_reset_token(payload.token)

    if not email:
        raise HTTPException(400, "Invalid or expired token")

    # update user password
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "Invalid user email or invalid token")

    user.set_password(payload.new_password)
    db.commit()

    return {"msg": "Password updated successfully"}


# EMAIL VERIFICATION FUNCTIONALITIES
@router.get("/verify-email/{email}")
async def send_verification_email(email: str, db: Session = Depends(get_db)):
    """Send verification email to user"""
    # Verify user exists
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=404, detail="User does not exist")

    # Check if already verified
    if user.confirmed_email:
        raise HTTPException(status_code=400, detail="Email already verified")

    # Generate verification token
    token = generate_reset_token(email)

    # Build verification URL using environment variable for frontend base URL
    frontend_base_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    verification_url = f"{frontend_base_url}/verify-email/{token}"

    # Send verification email using template "c106c91f-48bf-420d-82dc-aeb7fb5c08ff"
    await send_email(
        user.email,
        "Verify Your Email - Cocobase",
        "c106c91f-48bf-420d-82dc-aeb7fb5c08ff",
        {"verification_link": verification_url, "username": user.username},
    )

    return {"msg": "Verification email sent successfully"}


class EmailVerificationSchema(BaseModel):
    token: str


@router.post("/confirm-email")
def confirm_email_verification(
    payload: EmailVerificationSchema, db: Session = Depends(get_db)
):
    """Verify the email using the token"""
    # Verify token and get email
    email = verify_reset_token(payload.token)

    if not email:
        raise HTTPException(
            status_code=400, detail="Invalid or expired verification token"
        )

    # Get user and update verification status
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.confirmed_email:
        raise HTTPException(status_code=400, detail="Email already verified")

    # Update user verification status
    user.confirmed_email = True
    db.commit()
    db.refresh(user)

    return {
        "msg": "Email verified successfully",
        "user": {
            "email": user.email,
            "username": user.username,
            "is_verified": user.confirmed_email,
        },
    }


# Optional: Resend verification email endpoint
@router.post("/resend-verification")
async def resend_verification_email(email: str, db: Session = Depends(get_db)):
    """Resend verification email to user"""
    user = db.query(User).filter(User.email == email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User does not exist")

    if user.confirmed_email:
        raise HTTPException(status_code=400, detail="Email already verified")

    # Generate new verification token
    token = generate_reset_token(email)

    # Build verification URL
    frontend_base_url = os.environ.get("FRONTEND_URL", "http://localhost:5173")
    verification_url = f"{frontend_base_url}/verify-email/{token}"

    # Send verification email
    await send_email(
        user.email,
        "Verify Your Email - Cocobase",
        "c106c91f-48bf-420d-82dc-aeb7fb5c08ff",
        {"verification_link": verification_url, "username": user.username},
    )

    return {"msg": "Verification email resent successfully"}
