from pydantic import BaseModel
from typing import Optional


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    career: Optional[str] = None
    university_id: Optional[str] = None
    weekly_goal_kg: Optional[float] = None


class ProfileOut(BaseModel):
    id: str
    full_name: Optional[str] = None
    username: Optional[str] = None
    avatar_initials: Optional[str] = None
    university_id: Optional[str] = None
    career: Optional[str] = None
    points: int = 0
    total_kg: float = 0
    co2_saved_kg: float = 0
    streak_days: int = 0
    level_index: int = 0
    weekly_goal_kg: float = 5
    qr_code: Optional[str] = None
    is_plus: bool = False
    plus_expires_at: Optional[str] = None
