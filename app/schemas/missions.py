from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


class MissionOut(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    goal: Optional[float] = None
    active: Optional[bool] = None
    done: Optional[bool] = None
    completed_at: Optional[datetime] = None
    period_start: Optional[date] = None


class BadgeOut(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    unlocked_at: Optional[datetime] = None


class ChallengeOut(BaseModel):
    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    goal: Optional[float] = None
    active: Optional[bool] = None
    progress: Optional[float] = None
    completed: Optional[bool] = None


class CompleteMissionRequest(BaseModel):
    mission_id: str
    period_start: date
