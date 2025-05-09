# Define the root directory of your project
$projectName = "my_fastapi_project"
$rootDir = "$pwd\$projectName"

# Create the root directory
New-Item -Path $rootDir -ItemType Directory

# Create the core directories and files
$directories = @(
    "app",
    "app/models",
    "app/schemas",
    "app/crud",
    "app/api",
    "app/core",
    "app/services",
    "app/tests",
    "app/migrations/versions"
)

# Create directories
foreach ($dir in $directories) {
    New-Item -Path "$rootDir\$dir" -ItemType Directory -Force
}

# Create main.py in the app directory
$mainPyContent = @"
from fastapi import FastAPI
from app.api import user, document, collection

app = FastAPI()

# Include routers
app.include_router(user.router, prefix="/users", tags=["users"])
app.include_router(document.router, prefix="/documents", tags=["documents"])
app.include_router(collection.router, prefix="/collections", tags=["collections"])
"@
Set-Content -Path "$rootDir\app\main.py" -Value $mainPyContent

# Create a sample user.py model in app/models
$userModelContent = @"
from sqlalchemy import Column, Integer, String
from app.core.database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
"@
Set-Content -Path "$rootDir\app\models\user.py" -Value $userModelContent

# Create user schema in app/schemas
$userSchemaContent = @"
from pydantic import BaseModel

class UserBase(BaseModel):
    username: str
    email: str

class UserCreate(UserBase):
    password: str

class User(UserBase):
    id: int

    class Config:
        orm_mode = True
"@
Set-Content -Path "$rootDir\app\schemas\user.py" -Value $userSchemaContent

# Create user CRUD in app/crud
$userCrudContent = @"
from sqlalchemy.orm import Session
from app import models, schemas

def create_user(db: Session, user: schemas.UserCreate):
    db_user = models.User(**user.dict())
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()
"@
Set-Content -Path "$rootDir\app\crud\user.py" -Value $userCrudContent

# Create user API in app/api
$userApiContent = @"
from fastapi import APIRouter, HTTPException
from app import crud, schemas
from sqlalchemy.orm import Session
from app.core.database import get_db

router = APIRouter()

@router.post("/", response_model=schemas.User)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    return crud.create_user(db=db, user=user)

@router.get("/{user_id}", response_model=schemas.User)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = crud.get_user(db=db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
"@
Set-Content -Path "$rootDir\app\api\user.py" -Value $userApiContent

# Create database.py in app/core
$databasePyContent = @"
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

SQLALCHEMY_DATABASE_URL = settings.DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
"@
Set-Content -Path "$rootDir\app\core\database.py" -Value $databasePyContent

# Create config.py in app/core
$configPyContent = @"
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./test.db")
"@
Set-Content -Path "$rootDir\app\core\config.py" -Value $configPyContent

# Create Dockerfile for containerization
$dockerfileContent = @"
FROM python:3.9

# Set the working directory
WORKDIR /app

# Copy the current directory contents into the container
COPY . .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 8000 for FastAPI
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"@
Set-Content -Path "$rootDir\Dockerfile" -Value $dockerfileContent

# Create requirements.txt
$requirementsTxtContent = @"
fastapi
uvicorn
sqlalchemy
pydantic
python-dotenv
"@
Set-Content -Path "$rootDir\requirements.txt" -Value $requirementsTxtContent

# Create alembic.ini for database migrations
$alembicIniContent = @"
[alembic]
script_location = alembic
sqlalchemy.url = driver://user:pass@localhost/dbname
"@
Set-Content -Path "$rootDir\alembic.ini" -Value $alembicIniContent

# Create README.md
$readmeContent = @"
# My FastAPI Project

This is a FastAPI project that follows a modular structure with examples of users, CRUD operations, and database interaction.
"@
Set-Content -Path "$rootDir\README.md" -Value $readmeContent

# Initialize an empty Git repository
cd $rootDir
git init
