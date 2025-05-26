from datetime import datetime
from pydantic import BaseModel

from typing import Optional


class CollectionBase(BaseModel):
    name: str


class DocumentBase(BaseModel):
    data: dict


# * CREATE SCHEMAS
class CollectionCreateSchema(CollectionBase): ...


class DocumentCreateSchema(DocumentBase):
    collection_name: Optional[str] = None


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
    email:str

class AppUserCreate(AppUserBase):
    password:str


class AppUser(AppUserBase):
    id:str
    client_id:str
    created_at:datetime
    