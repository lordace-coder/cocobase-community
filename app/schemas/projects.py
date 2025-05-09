from pydantic import BaseModel, EmailStr
from typing import List, Optional
from uuid import UUID

class ProjectBase(BaseModel):
    name: str
    api_key: str
    allowed_origins: Optional[List[str]]

class ProjectCreate(ProjectBase):...

class ProjectUpdate(BaseModel):
    name: Optional[str]
    allowed_origins: Optional[List[str]]

class ProjectInDBBase(ProjectBase):
    id: UUID
    user_id: UUID
    created_at: Optional[str]



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
