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
    email_verified: bool = False
    email_verified_at: Optional[datetime] = None


class AppTokenResponse(BaseModel):
    access_token: Optional[str] = None
    user: Optional[AppUserResponse] = None
    # 2FA fields (returned when 2FA is required)
    requires_2fa: Optional[bool] = None
    message: Optional[str] = None
