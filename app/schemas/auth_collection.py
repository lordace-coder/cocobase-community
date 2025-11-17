from datetime import datetime
from typing import Optional
from pydantic import BaseModel




class AppUserSchema(BaseModel):
    email: str
    password: str
    data: Optional[dict] = None
    roles: Optional[list[str]] = []


class AppUserUpdateSchema(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None
    data: Optional[dict] = None
    roles: Optional[list[str]] = []


class AppUserResponse(BaseModel):
    email: str
    data: Optional[dict] = None
    client_id: str
    created_at: datetime
    id: str
    roles: Optional[list[str]] = []


class AppTokenResponse(BaseModel):
    access_token: str
    user:Optional[AppUserResponse] = None
