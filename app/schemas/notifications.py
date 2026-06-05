from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NotificationOut(BaseModel):
    id: str
    user_id: str
    title: Optional[str] = None
    body: Optional[str] = None
    read: bool = False
    created_at: Optional[datetime] = None


class UnreadCountOut(BaseModel):
    count: int
