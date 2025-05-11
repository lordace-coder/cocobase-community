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
    collection_name:Optional[str] = None



# * UPDATE SCHEMAS
class CollectionUpdateSchema(BaseModel):
    name: Optional[str] = None


# * VIEW SCHEMAS
class CollectionSchema(CollectionBase):
    id: str
    created_at: datetime


class DocumentSchema(DocumentBase):
    id: str
    collection_id: str
    created_at: datetime
    collection:CollectionSchema
