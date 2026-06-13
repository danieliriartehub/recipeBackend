from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Merchant Products ─────────────────────────────────────────────────────────

class MerchantProductCreate(BaseModel):
    merchant_partner_id: str
    name: str
    description: Optional[str] = None
    points: int
    stock: Optional[int] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    is_active: bool = True


class MerchantProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    points: Optional[int] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None


class MerchantProductOut(BaseModel):
    id: str
    merchant_partner_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    points: Optional[int] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


# ── Merchant Partners ─────────────────────────────────────────────────────────

class MerchantPartnerUpdate(BaseModel):
    name: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    cover_url: Optional[str] = None
    brand_color: Optional[str] = None
    category: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class MerchantPartnerOut(BaseModel):
    id: str
    name: Optional[str] = None
    tagline: Optional[str] = None
    description: Optional[str] = None
    logo_url: Optional[str] = None
    cover_url: Optional[str] = None
    brand_color: Optional[str] = None
    category: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None


class MerchantUserOut(BaseModel):
    id: str
    is_active: Optional[bool] = None
    merchant_partners: Optional[MerchantPartnerOut] = None


# ── Operator / Validator ───────────────────────────────────────────────────────

class ValidatorOut(BaseModel):
    id: str
    full_name: Optional[str] = None
    center_id: Optional[str] = None
    centers: Optional[dict] = None


class ValidateQrRequest(BaseModel):
    token: str
    validator_id: str
    center_id: str


class ValidateQrOut(BaseModel):
    valid: bool
    error: Optional[str] = None
    user_id: Optional[str] = None
    full_name: Optional[str] = None
    qr_code: Optional[str] = None
    points: Optional[int] = None
    center_id: Optional[str] = None
    validated_at: Optional[str] = None


class CreateDeliverySessionRequest(BaseModel):
    operator_id: str
    center_id: str


class AddDeliveryItemRequest(BaseModel):
    session_id: str
    material: str
    kg: float


class RemoveDeliveryItemRequest(BaseModel):
    session_id: str
    item_id: str


class ConfirmDeliveryRequest(BaseModel):
    session_id: str
    qr_token: str
    validator_id: str


class RegisterRecyclingRequest(BaseModel):
    token: str
    validator_id: str
    center_id: str
    material: str
    kg: float


# ── Marketplace ───────────────────────────────────────────────────────────────

class MarketplaceMerchantOut(BaseModel):
    id: str
    business_name: str = Field(alias="name")
    logo_url: Optional[str] = None


class MarketplaceProductListOut(BaseModel):
    id: str
    name: str
    short_description: Optional[str] = None
    points: int
    category: Optional[str] = None
    image_url: Optional[str] = None
    merchant: MarketplaceMerchantOut


class MarketplaceProductOut(BaseModel):
    id: str
    name: str
    short_description: Optional[str] = None
    description: Optional[str] = None
    points: int
    stock: Optional[int] = None
    category: Optional[str] = None
    image_url: Optional[str] = None
    featured: bool = False
    available_from: Optional[datetime] = None
    available_until: Optional[datetime] = None
    terms_and_conditions: Optional[str] = None
    redemption_instructions: Optional[str] = None
    merchant: MarketplaceMerchantOut
