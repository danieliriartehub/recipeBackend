from pydantic import BaseModel
from typing import Optional, List


class CenterOut(BaseModel):
    id: str
    name: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    status: Optional[str] = None
    accepted_materials: Optional[List[str]] = None
    hours: Optional[str] = None
    wait_minutes: Optional[int] = None
    capacity: Optional[int] = None
    rating: Optional[float] = None
