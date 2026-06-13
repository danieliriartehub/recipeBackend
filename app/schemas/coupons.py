from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CouponHistoryOut(BaseModel):
    coupon_id: str
    reward_id: str
    title: Optional[str] = None
    brand: Optional[str] = None
    emoji: Optional[str] = None
    code: Optional[str] = None
    points_spent: Optional[int] = None
    used_at: Optional[datetime] = None
