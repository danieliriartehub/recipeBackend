"""
test_schemas.py
"""
import pytest
from pydantic import ValidationError

from app.schemas.profiles import ProfileOut, ProfileUpdate
from app.schemas.recyclings import RecyclingCreate, RecyclingOut
from app.schemas.wallet import WalletBalanceOut, WalletHistoryOut
from app.schemas.marketplace import RedeemProductRequest, RedemptionOut
from app.schemas.centers import CenterOut
from app.schemas.aliados import (
    MarketplaceMerchantOut,
    MarketplaceProductListOut,
    MarketplaceProductOut,
    MerchantPartnerOut,
)

class TestProfileUpdate:
    def test_all_fields_optional(self):
        update = ProfileUpdate()
        assert update.model_dump(exclude_none=True) == {}

    def test_accepts_valid_fields(self):
        update = ProfileUpdate(full_name="Juan Pérez", username="juanp")
        assert update.full_name == "Juan Pérez"
        assert update.username == "juanp"

class TestRecyclingCreate:
    def test_valid_recycling(self):
        recycling = RecyclingCreate(
            material="Plástico",
            kg=1.5,
            points_earned=150,
            co2_saved_kg=0.75,
            center_id="center-001",
        )
        assert recycling.material == "Plástico"
        assert recycling.kg == 1.5

    def test_missing_required_fields(self):
        with pytest.raises(ValidationError):
            RecyclingCreate(kg=1.5, points_earned=150)

class TestWalletBalanceOut:
    def test_valid_balance(self):
        balance = WalletBalanceOut(
            user_id="user-001",
            current_balance=500.0,
            total_earned=800.0,
            total_spent=300.0,
            total_kg=15.0,
            co2_saved_kg=7.5,
            streak_days=5,
            total_recyclings=8,
        )
        assert balance.current_balance == 500.0
        assert balance.streak_days == 5

class TestRedeemProductRequest:
    def test_valid_request(self):
        req = RedeemProductRequest(product_id="product-001")
        assert req.product_id == "product-001"

    def test_missing_product_id(self):
        with pytest.raises(ValidationError):
            RedeemProductRequest()

class TestMarketplaceMerchantOut:
    def test_valid_merchant(self):
        merchant = MarketplaceMerchantOut(
            id="merchant-001",
            name="EcoLima",
            logo_url="https://example.com/logo.png",
        )
        assert merchant.id == "merchant-001"

    def test_logo_url_optional(self):
        merchant = MarketplaceMerchantOut(id="merchant-001", name="EcoLima")
        assert merchant.logo_url is None

class TestMarketplaceProductListOut:
    def test_valid_product_list_item(self):
        merchant = MarketplaceMerchantOut(id="merchant-001", name="EcoLima")
        product = MarketplaceProductListOut(
            id="product-001",
            name="Café gratis",
            short_description="Café por tu reciclaje",
            points=500,
            category="Cafetería",
            image_url="https://example.com/cafe.png",
            merchant=merchant,
        )
        assert product.name == "Café gratis"
        assert product.points == 500

class TestCenterOut:
    def test_valid_center(self):
        center = CenterOut(
            id="center-001",
            name="Centro Norte",
            district="Miraflores",
            address="Av. Principal 123",
            lat=-12.1234,
            lng=-77.0234,
            status="disponible",
        )
        assert center.name == "Centro Norte"
        assert center.status == "disponible"

    def test_optional_fields_default_none(self):
        center = CenterOut(id="c-001", name="Test", district="Lima")
        assert center.lat is None
        assert center.lng is None
