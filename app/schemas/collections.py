from datetime import datetime
from pydantic import BaseModel
from app.core.config import DEFAULT_PERMISSION_DICT
from typing import Optional


class CollectionPermissionsRequest(BaseModel):
    create: list = []
    read: list = []
    update: list = []
    delete: list = []


class CollectionBase(BaseModel):
    name: str
    model_config = {"from_attributes": True}  # replaces orm_mode = True
    webhook_url: Optional[str] = None
    permissions: Optional[CollectionPermissionsRequest] = DEFAULT_PERMISSION_DICT


class DocumentBase(BaseModel):
    data: dict | None = None

    model_config = {"from_attributes": True}  # replaces orm_mode = True


# * CREATE SCHEMAS
class CollectionCreateSchema(CollectionBase): ...


class DocumentCreateSchema(DocumentBase): ...


# * UPDATE SCHEMAS
class CollectionUpdateSchema(BaseModel):
    name: Optional[str] = None


class DocumentUpdateSchema(BaseModel):
    data: dict


# * VIEW SCHEMAS


class CollectionSchema(CollectionBase):
    id: str
    created_at: datetime


class DocumentSchema(DocumentBase):
    id: str
    collection_id: str
    created_at: datetime
    collection: CollectionSchema


# * AUTH SCHEMAS


class AppUserBase(BaseModel):
    email: str


class AppUserCreate(AppUserBase):
    password: str


class AppUser(AppUserBase):
    id: str
    client_id: str
    created_at: datetime
