from fastapi import APIRouter, HTTPException,Depends,status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.schemas.user import UserSchema, UserCreateSchema
from app.models.user import User
from app.services.jwt import create_access_token

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")

@router.post("/", status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreateSchema, db: Session = Depends(get_db)) -> UserSchema:
    # check if user exists
    user = User(**payload.dict())
    user.set_password(payload.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email}


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
