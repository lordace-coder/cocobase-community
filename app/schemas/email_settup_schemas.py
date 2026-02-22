from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum

from app.models.email_models import EmailStatusEnum, EmailTemplateTypeEnum

# ============= Pydantic Schemas =============

class SMTPConfigCreate(BaseModel):
    host: str
    port: int = 587
    username: str
    password: str
    use_tls: bool = True
    use_ssl: bool = False
    from_email: EmailStr
    from_name: str = ""


class SMTPConfigUpdate(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    use_tls: Optional[bool] = None
    use_ssl: Optional[bool] = None
    from_email: Optional[EmailStr] = None
    from_name: Optional[str] = None
    is_active: Optional[bool] = None


class SMTPConfigResponse(BaseModel):
    id: int
    project_id: str
    host: str
    port: int
    username: str
    use_tls: bool
    use_ssl: bool
    from_email: str
    from_name: str
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateCreate(BaseModel):
    template_type: EmailTemplateTypeEnum
    name: str
    description: str = ""
    subject: str
    html_body: str
    text_body: str
    available_variables: dict = {}


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    html_body: Optional[str] = None
    text_body: Optional[str] = None
    available_variables: Optional[dict] = None
    is_active: Optional[bool] = None


class TemplateResponse(BaseModel):
    id: int
    template_type: EmailTemplateTypeEnum
    name: str
    description: str
    subject: str
    html_body: str
    text_body: str
    available_variables: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectTemplateResponse(TemplateResponse):
    project_id: str
    is_default_override: bool
    created_by: str


class SendEmailRequest(BaseModel):
    recipients: List[EmailStr]
    body:str
    subject: str


class EmailLogResponse(BaseModel):
    id: int
    project_id: str
    recipients: List[str]
    subject: str
    template_type: EmailTemplateTypeEnum
    status: EmailStatusEnum
    error_message: str
    sent_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class EmailProviderResponse(BaseModel):
    provider_type: str  # "smtp", "cocomailer", "resend", "emailjs"
    config: dict
    is_active: bool
