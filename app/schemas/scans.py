from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ScanCreate(BaseModel):
    item_name: str
    material: str
    recyclable: bool
    confidence: float
    tip: Optional[str] = None
    nearest_center_id: Optional[str] = None
    estimated_points: Optional[int] = None
    image_url: Optional[str] = None


class ScanOut(BaseModel):
    id: str
    user_id: str
    item_name: Optional[str] = None
    material: Optional[str] = None
    recyclable: Optional[bool] = None
    confidence: Optional[float] = None
    tip: Optional[str] = None
    nearest_center_id: Optional[str] = None
    estimated_points: Optional[int] = None
    image_url: Optional[str] = None
    created_at: Optional[datetime] = None
