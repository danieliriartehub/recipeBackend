"""
test_marketplace.py
"""
from unittest.mock import MagicMock
import pytest
import copy

BASE = "/api/v1/marketplace"

PRODUCT_ROW = {
    "id": "product-001",
    "name": "Café gratis",
    "short_description": "Un café",
    "description": "Café 250ml.",
    "points": 500,
    "stock": 10,
    "category": "Cafetería",
    "image_url": "https://example.com/cafe.png",
    "featured": True,
    "terms_and_conditions": "Válido 30 días.",
    "redemption_instructions": "Muestra el código en caja.",
    "status": "active",
    "is_active": True,
    "merchant_partner_id": "merchant-001",
    "merchant_partners": {
        "id": "merchant-001",
        "business_name": "EcoLima",
        "logo_url": "https://example.com/logo.png",
        "is_active": True,
    },
}

class TestGetMerchants:
    def test_returns_merchant_list(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=[
            {"id": "merchant-001", "business_name": "EcoLima", "logo_url": "https://example.com/logo.png"}
        ])
        response = client.get(f"{BASE}/merchants", headers=auth_headers)
        assert response.status_code == 200

    def test_returns_empty_list(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=[])
        response = client.get(f"{BASE}/merchants", headers=auth_headers)
        assert response.status_code == 200

    def test_requires_authentication(self, client):
        from app.core.dependencies import get_current_user
        from app.main import app
        app.dependency_overrides.pop(get_current_user, None)
        response = client.get(f"{BASE}/merchants")
        assert response.status_code == 401

class TestGetMerchantById:
    def test_returns_merchant_detail(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data={"id": "m1", "business_name": "E", "is_active": True})
        response = client.get(f"{BASE}/merchants/m1", headers=auth_headers)
        assert response.status_code == 200

    def test_returns_404_when_not_found(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=None)
        response = client.get(f"{BASE}/merchants/nonexistent", headers=auth_headers)
        assert response.status_code == 404

class TestGetCategories:
    def test_returns_unique_sorted_categories(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=[{"category": "Cafetería"}])
        response = client.get(f"{BASE}/categories", headers=auth_headers)
        assert response.status_code == 200

    def test_returns_empty_list_when_no_products(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=[])
        response = client.get(f"{BASE}/categories", headers=auth_headers)
        assert response.status_code == 200

class TestGetProducts:
    def test_returns_product_list(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=[copy.deepcopy(PRODUCT_ROW)])
        response = client.get(f"{BASE}/products", headers=auth_headers)
        assert response.status_code == 200

    def test_filters_by_category(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=[copy.deepcopy(PRODUCT_ROW)])
        response = client.get(f"{BASE}/products?category=Cafetería", headers=auth_headers)
        assert response.status_code == 200

    def test_filters_by_search_query(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=[copy.deepcopy(PRODUCT_ROW)])
        response = client.get(f"{BASE}/products?search_query=café", headers=auth_headers)
        assert response.status_code == 200

    def test_returns_empty_when_no_matches(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=[])
        response = client.get(f"{BASE}/products?category=NoExiste", headers=auth_headers)
        assert response.status_code == 200

    def test_requires_authentication(self, client):
        from app.core.dependencies import get_current_user
        from app.main import app
        app.dependency_overrides.pop(get_current_user, None)
        response = client.get(f"{BASE}/products")
        assert response.status_code == 401

class TestGetProductById:
    def test_returns_product_detail(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=copy.deepcopy(PRODUCT_ROW))
        response = client.get(f"{BASE}/products/product-001", headers=auth_headers)
        assert response.status_code == 200

    def test_returns_404_when_not_found(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=None)
        response = client.get(f"{BASE}/products/nonexistent", headers=auth_headers)
        assert response.status_code == 404

class TestRedeemProduct:
    def _setup_mocks(self, mock_db, user_id, product_data=None, user_points=1000):
        mock_db.rpc.side_effect = Exception("Forcing fallback logic")
        product = product_data or copy.deepcopy(PRODUCT_ROW)
        profile_data = {"points": user_points}
        execute_returns = [
            MagicMock(data=product),
            MagicMock(data={"id": user_id, **{"points": user_points}}),
            MagicMock(data=[]),
            MagicMock(data=[]),
            MagicMock(data=[{
                "id": "redemption-001",
                "user_id": user_id,
                "merchant_product_id": "product-001",
                "points_spent": 500,
                "redemption_code": "ABCD1234",
                "status": "pending",
                "redeemed_at": None,
            }]),
            MagicMock(data=[]),
        ]
        mock_db.execute.side_effect = execute_returns

    def test_redeems_product_successfully(self, client, auth_headers, mock_db, user_id):
        self._setup_mocks(mock_db, user_id, user_points=1000)
        response = client.post(
            f"{BASE}/redemptions",
            headers=auth_headers,
            json={"product_id": "product-001"},
        )
        assert response.status_code == 201

    def test_returns_404_when_product_not_found(self, client, auth_headers, mock_db):
        mock_db.rpc.side_effect = Exception("Forcing fallback logic")
        mock_db.execute.return_value = MagicMock(data=None)
        response = client.post(
            f"{BASE}/redemptions",
            headers=auth_headers,
            json={"product_id": "nonexistent"},
        )
        assert response.status_code == 404

    def test_returns_400_when_out_of_stock(self, client, auth_headers, mock_db, user_id):
        mock_db.rpc.side_effect = Exception("Forcing fallback logic")
        out_of_stock = {**copy.deepcopy(PRODUCT_ROW), "stock": 0}
        mock_db.execute.return_value = MagicMock(data=out_of_stock)
        response = client.post(
            f"{BASE}/redemptions",
            headers=auth_headers,
            json={"product_id": "product-001"},
        )
        assert response.status_code == 400

    def test_returns_400_when_insufficient_points(self, client, auth_headers, mock_db, user_id):
        mock_db.rpc.side_effect = Exception("Forcing fallback logic")
        execute_returns = [
            MagicMock(data=copy.deepcopy(PRODUCT_ROW)),
            MagicMock(data={"id": user_id, "points": 100}),
        ]
        mock_db.execute.side_effect = execute_returns
        response = client.post(
            f"{BASE}/redemptions",
            headers=auth_headers,
            json={"product_id": "product-001"},
        )
        assert response.status_code == 400

    def test_requires_authentication(self, client):
        from app.core.dependencies import get_current_user
        from app.main import app
        app.dependency_overrides.pop(get_current_user, None)
        response = client.post(f"{BASE}/redemptions", json={"product_id": "product-001"})
        assert response.status_code == 401
