from datetime import datetime
from pydantic import BaseModel, Field



class NotificationSchema(BaseModel):
    id: int
    user_id: str
    message: str 
    is_read: bool = False
    created: datetime