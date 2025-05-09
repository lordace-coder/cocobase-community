from datetime import datetime
from pydantic import BaseModel
from sqlalchemy import UUID

class CollectionBase(BaseModel):
    name:str

class DocumentBase(BaseModel):
    data: dict


# * CREATE SCHEMAS
class CollectionCreateSchema(CollectionBase):...

class DocumentCreateSchema(DocumentBase):...

# * VIEW SCHEMAS
class CollectionSchema(CollectionBase):
    id:UUID
    user_id:UUID
    created_at: datetime


class DocumentSchema(CollectionBase):
    id:UUID
    collection_id:UUID
    created_at: datetime