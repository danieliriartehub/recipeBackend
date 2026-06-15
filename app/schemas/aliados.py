from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


# ── Merchant Products ─────────────────────────────────────────────────────────

class GenerateProductDetailsRequest(BaseModel):
    name: str

class GenerateProductDetailsOut(BaseModel):
    description: str
    category: str


class MerchantProductCreate(BaseModel):
    merchant_partner_id: str
    name: str
    description: Optional[str] = None
    points: int
    stock: Optional[int] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    is_active: bool = True
    expiration_days: Optional[int] = None


class MerchantProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    points: Optional[int] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None
    category: Optional[str] = None
    is_active: Optional[bool] = None
    expiration_days: Optional[int] = None


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
    expiration_days: Optional[int] = None
    created_at: Optional[datetime] = None


# ── Merchant Partners ─────────────────────────────────────────────────────────

class MerchantPartnerUpdate(BaseModel):
    business_name: Optional[str] = None
    tagline: Optional[str] = None
    profile_description: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    brand_color: Optional[str] = None
    category: Optional[str] = None
    contact_email: Optional[str] = None
    website_url: Optional[str] = None


class MerchantPartnerOut(BaseModel):
    id: str
    business_name: Optional[str] = None
    tagline: Optional[str] = None
    profile_description: Optional[str] = None
    logo_url: Optional[str] = None
    banner_url: Optional[str] = None
    brand_color: Optional[str] = None
    category: Optional[str] = None
    contact_email: Optional[str] = None
    website_url: Optional[str] = None


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
    expiration_days: Optional[int] = None
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
    expiration_days: Optional[int] = None
    terms_and_conditions: Optional[str] = None
    redemption_instructions: Optional[str] = None
    merchant: MarketplaceMerchantOut

# ── Merchant Banners ──────────────────────────────────────────────────────────

class MerchantBannerCreate(BaseModel):
    title: Optional[str] = None
    link_url: Optional[str] = None
    is_active: bool = True
    display_order: int = 0

class MerchantBannerUpdate(BaseModel):
    title: Optional[str] = None
    link_url: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

class MerchantBannerOut(BaseModel):
    id: str
    merchant_partner_id: str
    title: Optional[str] = None
    banner_url: str
    link_url: Optional[str] = None
    is_active: bool
    display_order: int
    created_at: Optional[datetime] = None
    is_ml_targeted: Optional[bool] = None

class AdTrackingRequest(BaseModel):
    banner_id: str
    action: str

