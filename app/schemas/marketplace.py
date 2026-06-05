from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RewardOut(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    points: Optional[int] = None
    active: Optional[bool] = None


class MarketItemOut(BaseModel):
    id: str
    name: Optional[str] = None
    description: Optional[str] = None
    points: Optional[int] = None
    active: Optional[bool] = None
    image_url: Optional[str] = None


class UserCouponOut(BaseModel):
    id: str
    user_id: str
    reward_id: str
    code: Optional[str] = None
    created_at: Optional[datetime] = None
    rewards: Optional[RewardOut] = None


class RedeemRewardRequest(BaseModel):
    reward_id: str
    code: str
