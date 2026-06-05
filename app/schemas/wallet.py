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


class WalletEntryOut(BaseModel):
    id: str
    user_id: str
    amount: Optional[float] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None


class WalletHistoryOut(BaseModel):
    id: str
    user_id: str
    amount: Optional[float] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
