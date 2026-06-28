"""
test_profiles.py
"""
from unittest.mock import MagicMock
import pytest

BASE = "/api/v1/profiles"

class TestGetMyProfile:
    def test_returns_profile_successfully(self, client, auth_headers, mock_db, user_id):
        mock_db.execute.return_value = MagicMock(data={
            "id": user_id,
            "full_name": "Test User",
            "username": "testuser",
            "points": 500,
            "total_kg": 10.5,
            "co2_saved_kg": 5.25,
            "streak_days": 3,
            "level_index": 1,
            "university_id": None,
            "career": None,
            "qr_code": "ABC123",
            "avatar_initials": "TU",
            "weekly_goal_kg": 5.0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        })
        response = client.get(f"{BASE}/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == user_id
        assert data["full_name"] == "Test User"
        assert data["points"] == 500

    def test_returns_404_when_profile_not_found(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=None)
        response = client.get(f"{BASE}/me", headers=auth_headers)
        assert response.status_code == 404

class TestUpdateMyProfile:
    def test_updates_profile_successfully(self, client, auth_headers, mock_db, user_id):
        mock_db.execute.return_value = MagicMock(data=[{
            "id": user_id,
            "full_name": "Nuevo Nombre",
            "username": "nuevouser",
            "points": 500,
            "total_kg": 10.5,
            "co2_saved_kg": 5.25,
            "streak_days": 3,
            "level_index": 1,
            "university_id": None,
            "career": None,
            "qr_code": "ABC123",
            "avatar_initials": "NN",
            "weekly_goal_kg": 5.0,
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-06-01T00:00:00Z",
        }])
        response = client.patch(
            f"{BASE}/me",
            headers=auth_headers,
            json={"full_name": "Nuevo Nombre", "username": "nuevouser"},
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Nuevo Nombre"

    def test_returns_400_when_no_fields_provided(self, client, auth_headers, mock_db):
        response = client.patch(f"{BASE}/me", headers=auth_headers, json={})
        assert response.status_code == 400

    def test_returns_404_when_profile_not_found_on_update(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=[])
        response = client.patch(
            f"{BASE}/me",
            headers=auth_headers,
            json={"full_name": "Test"},
        )
        assert response.status_code == 404

    def test_returns_400_on_duplicate_username(self, client, auth_headers, mock_db):
        mock_db.execute.side_effect = Exception("duplicate key value violates unique constraint")
        response = client.patch(
            f"{BASE}/me",
            headers=auth_headers,
            json={"username": "duplicado"},
        )
        assert response.status_code == 400

class TestGenerateQrToken:
    def test_generates_token_successfully(self, client, auth_headers, mock_db, user_id):
        mock_db.execute.return_value = MagicMock(data={
            "full_name": "Test User",
            "qr_code": "QR001",
            "points": 500,
        })
        response = client.post(f"{BASE}/me/qr-token", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["expires_in"] == 60

    def test_returns_404_when_profile_missing(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=None)
        response = client.post(f"{BASE}/me/qr-token", headers=auth_headers)
        assert response.status_code == 404
