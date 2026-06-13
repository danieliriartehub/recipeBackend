from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.schemas.aliados import MarketplaceProductOut


class RedeemProductRequest(BaseModel):
    product_id: str


class RedemptionOut(BaseModel):
    id: str
    user_id: str
    merchant_product_id: str
    points_spent: int
    redemption_code: str
    status: Optional[str] = None
    redeemed_at: Optional[datetime] = None
    product: Optional[MarketplaceProductOut] = None
