from pydantic import BaseModel
from typing import Optional
from datetime import datetime


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
    redeemed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class CouponValidateOut(BaseModel):
    redemption_id: str
    product_id: str
    product_name: str
    partner_name: str
    points_spent: int
    redemption_code: str
    status: str
    expires_at: Optional[datetime] = None


class CouponRedeemRequest(BaseModel):
    redemption_id: str


class CouponRedeemOut(BaseModel):
    success: bool
    message: str
