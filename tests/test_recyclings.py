"""
test_recyclings.py
"""
from unittest.mock import MagicMock
import pytest

BASE = "/api/v1/recyclings"

class TestGetRecyclings:
    def test_returns_empty_list(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=[])
        response = client.get(f"{BASE}/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_recycling_list(self, client, auth_headers, mock_db, user_id):
        mock_db.execute.return_value = MagicMock(data=[
            {
                "id": "rec-001",
                "user_id": user_id,
                "material": "Plástico",
                "kg": 1.5,
                "points_earned": 150,
                "co2_saved_kg": 0.75,
                "center_id": "center-001",
                "created_at": "2024-06-01T10:00:00Z",
                "centers": {"name": "Centro Norte", "district": "Miraflores"},
            }
        ])
        response = client.get(f"{BASE}/", headers=auth_headers)
        assert response.status_code == 200
        assert len(response.json()) == 1

    def test_pagination_params_are_accepted(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=[])
        response = client.get(f"{BASE}/?skip=10&limit=5", headers=auth_headers)
        assert response.status_code == 200

    def test_requires_authentication(self, client):
        from app.core.dependencies import get_current_user
        from app.main import app
        app.dependency_overrides.pop(get_current_user, None)
        response = client.get(f"{BASE}/")
        assert response.status_code == 401

class TestCreateRecycling:
    def test_creates_recycling_and_wallet_entry(self, client, auth_headers, mock_db, user_id):
        created_recycling = {
            "id": "rec-new",
            "user_id": user_id,
            "material": "Vidrio",
            "kg": 3.0,
            "points_earned": 300,
            "co2_saved_kg": 1.5,
            "center_id": "center-001",
            "created_at": "2024-06-10T10:00:00Z",
            "centers": None,
        }
        mock_db.execute.return_value = MagicMock(data=created_recycling)
        response = client.post(
            f"{BASE}/",
            headers=auth_headers,
            json={
                "material": "Vidrio",
                "kg": 3.0,
                "points_earned": 300,
                "co2_saved_kg": 1.5,
                "center_id": "center-001",
            },
        )
        assert response.status_code == 201

    def test_creates_recycling_without_wallet_entry_when_zero_points(
        self, client, auth_headers, mock_db, user_id
    ):
        created_recycling = {
            "id": "rec-zero",
            "user_id": user_id,
            "material": "Otro",
            "kg": 0.5,
            "points_earned": 0,
            "co2_saved_kg": 0.25,
            "center_id": "center-001",
            "created_at": "2024-06-10T10:00:00Z",
            "centers": None,
        }
        mock_db.execute.return_value = MagicMock(data=created_recycling)
        response = client.post(
            f"{BASE}/",
            headers=auth_headers,
            json={"material": "Otro", "kg": 0.5, "points_earned": 0, "co2_saved_kg": 0.25, "center_id": "center-001"},
        )
        assert response.status_code == 201

    def test_requires_authentication(self, client):
        from app.core.dependencies import get_current_user
        from app.main import app
        app.dependency_overrides.pop(get_current_user, None)
        response = client.post(f"{BASE}/", json={"material": "Papel", "kg": 1.0, "points_earned": 10, "co2_saved_kg": 0.5, "center_id": "c1"})
        assert response.status_code == 401
