"""
test_wallet.py
"""
from unittest.mock import MagicMock
import pytest

BASE = "/api/v1/wallet"

class TestGetBalance:
    def test_returns_balance_successfully(self, client, auth_headers, mock_db, user_id):
        mock_db.execute.return_value = MagicMock(data={
            "user_id": user_id,
            "current_balance": 1500.0,
            "total_earned": 2000.0,
            "total_spent": 500.0,
            "total_kg": 25.0,
            "co2_saved_kg": 12.5,
            "streak_days": 7,
            "total_recyclings": 10,
        })
        response = client.get(f"{BASE}/balance", headers=auth_headers)
        assert response.status_code == 200

    def test_returns_404_when_balance_not_found(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=None)
        response = client.get(f"{BASE}/balance", headers=auth_headers)
        assert response.status_code == 404

    def test_requires_authentication(self, client):
        from app.core.dependencies import get_current_user
        from app.main import app
        app.dependency_overrides.pop(get_current_user, None)
        response = client.get(f"{BASE}/balance")
        assert response.status_code == 401

class TestGetHistory:
    def test_returns_full_history(self, client, auth_headers, mock_db, user_id):
        mock_db.execute.return_value = MagicMock(data=[
            {
                "id": "entry-001",
                "user_id": user_id,
                "points": 300,
                "type": "earned",
                "title": "Reciclaje",
                "created_at": "2024-06-01T10:00:00Z",
            }
        ])
        response = client.get(f"{BASE}/history", headers=auth_headers)
        assert response.status_code == 200

    def test_returns_empty_history(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=[])
        response = client.get(f"{BASE}/history", headers=auth_headers)
        assert response.status_code == 200

    def test_pagination_params_accepted(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=[])
        response = client.get(f"{BASE}/history?skip=5&limit=10", headers=auth_headers)
        assert response.status_code == 200

class TestGetRecentHistory:
    def test_returns_recent_entries(self, client, auth_headers, mock_db, user_id):
        mock_db.execute.return_value = MagicMock(data=[
            {
                "id": f"e{i}",
                "user_id": user_id,
                "points": 100,
                "type": "earned",
                "title": "Test",
                "created_at": "2024-06-01T10:00:00Z",
            } for i in range(3)
        ])
        response = client.get(f"{BASE}/history/recent", headers=auth_headers)
        assert response.status_code == 200

class TestSoftDeleteEntry:
    def test_soft_deletes_entry_successfully(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=[{"id": "entry-001"}])
        response = client.delete(f"{BASE}/entries/entry-001", headers=auth_headers)
        assert response.status_code == 204

    def test_returns_404_when_entry_not_found(self, client, auth_headers, mock_db):
        mock_db.execute.return_value = MagicMock(data=[])
        response = client.delete(f"{BASE}/entries/nonexistent", headers=auth_headers)
        assert response.status_code == 404

    def test_requires_authentication(self, client):
        from app.core.dependencies import get_current_user
        from app.main import app
        app.dependency_overrides.pop(get_current_user, None)
        response = client.delete(f"{BASE}/entries/entry-001")
        assert response.status_code == 401
