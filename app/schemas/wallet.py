from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class WalletBalanceOut(BaseModel):
    user_id: str
    current_balance: float
    total_earned: float
    total_spent: float
    total_kg: float
    co2_saved_kg: float
    streak_days: int
    total_recyclings: int


class WalletHistoryOut(BaseModel):
    id: str
    user_id: str
    points: Optional[int] = None
    type: Optional[str] = None
    title: Optional[str] = None
    detail: Optional[str] = None
    emoji: Optional[str] = None
    related_recycling_id: Optional[str] = None
    related_coupon_id: Optional[str] = None
    created_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
