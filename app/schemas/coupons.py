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


class MerchantCouponHistoryOut(BaseModel):
    redemption_id: str
    product_id: str
    product_name: str
    partner_name: str
    partner_logo: Optional[str] = None
    image_url: Optional[str] = None
    points_spent: int
    redemption_code: str
    status: str
    redeemed_at: datetime
