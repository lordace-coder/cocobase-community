from pydantic import BaseModel
from enum import Enum


class FileResponse(BaseModel):
    url: str


class FileType(str, Enum):
    image = "image"
    video = "video"
    other = "other"


class UploadedFileSchema(BaseModel):
    id: int
    user_id: str
    url: str
    public_id: str
    format: str | None
    file_type: FileType
    size: int

    class Config:
        orm_mode = True
