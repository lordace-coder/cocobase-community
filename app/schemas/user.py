from datetime import datetime
from pydantic import BaseModel
from uuid import UUID


class UserBase(BaseModel):
    username: str
    email: str
    full_name: str | None = None
    google_id: str | None = None
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


class UserCreateSchema(UserBase):
    password: str


class UserSchema(UserBase):
    id: UUID


class TeamMemberSchema(BaseModel):
    email: str
    role: str  # e.g., 'admin', 'member'
    model_config = {"from_attributes": True}
