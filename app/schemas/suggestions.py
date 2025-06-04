from datetime import datetime
from pydantic import BaseModel
from typing import List


class SuggestionBase(BaseModel):
    name: str
    description: str


class SuggestionCreate(SuggestionBase):
    pass


class SuggestionSchema(SuggestionBase):
    id: str
    created_at: datetime
    likes_count: int = 0
    has_liked: bool = False

