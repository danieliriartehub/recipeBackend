from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RecyclingCreate(BaseModel):
    center_id: str
    material: str
    kg: float
    points_earned: int
    co2_saved_kg: float


class RecyclingOut(BaseModel):
    id: str
    user_id: str
    center_id: Optional[str] = None
    material: Optional[str] = None
    kg: Optional[float] = None
    points_earned: Optional[int] = None
    co2_saved_kg: Optional[float] = None
    created_at: Optional[datetime] = None
