from pydantic import BaseModel



class FilesSchema(BaseModel):
    filename:str
    size:int
    url:str
    last_modified:str
    etag:str
