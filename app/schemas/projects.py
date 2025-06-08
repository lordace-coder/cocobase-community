from datetime import datetime
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from uuid import UUID

from app.schemas.user import UserSchema

class ProjectBase(BaseModel):
    name: str
    callback_url:Optional[str]=None
    api_key: Optional[str] = None  # Correct
    allowed_origins: Optional[List[str]] = None  # Correct

class ProjectCreate(ProjectBase):...

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    allowed_origins: Optional[List[str]] = None

class ProjectInDBBase(ProjectBase):
    id: UUID
    user_id: UUID
    created_at: Optional[datetime]
    owner:UserSchema



class Project(ProjectInDBBase):
    pass

class AppUserBase(BaseModel):
    email: EmailStr

class AppUserCreate(AppUserBase):
    password: str
    client_id: UUID

class AppUserUpdate(BaseModel):
    email: Optional[EmailStr]
    password: Optional[str]

class AppUserInDBBase(AppUserBase):
    id: UUID
    client_id: UUID
    created_at: Optional[str]
    oauth_id: Optional[str]

class AppUser(AppUserInDBBase):
    pass
