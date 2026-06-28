"""
test_auth.py
"""
from unittest.mock import MagicMock
import pytest

BASE = "/api/v1/auth"

def _make_fake_supabase_user():
    user = MagicMock()
    user.id = "00000000-0000-0000-0000-000000000001"
    user.email = "test@recipe.app"
    user.email_confirmed_at = "2024-01-01T00:00:00Z"
    user.user_metadata = {"full_name": "Test User"}
    return user

def _make_fake_session():
    session = MagicMock()
    session.access_token = "fake-access-token"
    session.refresh_token = "fake-refresh-token"
    session.expires_in = 3600
    session.user = _make_fake_supabase_user()
    return session

class TestLogin:
    def test_login_successful(self, client, mock_db):
        fake_session = _make_fake_session()
        auth_response = MagicMock()
        auth_response.session = fake_session
        auth_response.user = fake_session.user
        mock_db.auth.sign_in_with_password.return_value = auth_response

        response = client.post(f"{BASE}/login", json={
            "email": "test@recipe.app",
            "password": "password123",
        })
        assert response.status_code == 200
        data = response.json()
        assert "session" in data
        assert data["session"]["access_token"] == "fake-access-token"
        assert data["session"]["user"]["email"] == "test@recipe.app"

    def test_login_invalid_credentials(self, client, mock_db):
        mock_db.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")
        response = client.post(f"{BASE}/login", json={
            "email": "wrong@recipe.app",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    def test_login_missing_fields(self, client, mock_db):
        response = client.post(f"{BASE}/login", json={"email": "test@recipe.app"})
        assert response.status_code == 422

class TestRegister:
    def test_register_successful(self, client, mock_db):
        fake_session = _make_fake_session()
        auth_response = MagicMock()
        auth_response.session = fake_session
        auth_response.user = fake_session.user
        mock_db.auth.sign_up.return_value = auth_response

        response = client.post(f"{BASE}/register", json={
            "email": "new@recipe.app",
            "password": "securepass123",
            "full_name": "New User",
        })
        assert response.status_code in [200, 201]

    def test_register_missing_email(self, client, mock_db):
        response = client.post(f"{BASE}/register", json={
            "password": "securepass123",
            "full_name": "New User",
        })
        assert response.status_code == 422

class TestLogout:
    def test_logout_successful(self, client, auth_headers, mock_db):
        mock_db.auth.sign_out.return_value = None
        response = client.post(f"{BASE}/logout", headers=auth_headers)
        assert response.status_code in [200, 204]

class TestForgotPassword:
    def test_forgot_password_sends_email(self, client, mock_db):
        mock_db.auth.reset_password_email.return_value = None
        response = client.post(f"{BASE}/forgot-password", json={
            "email": "test@recipe.app",
        })
        assert response.status_code == 204

    def test_forgot_password_missing_email(self, client, mock_db):
        response = client.post(f"{BASE}/forgot-password", json={})
        assert response.status_code == 422

class TestGetMe:
    def test_returns_current_user(self, client, auth_headers, mock_db):
        fake_user = _make_fake_supabase_user()
        auth_get_response = MagicMock()
        auth_get_response.user = fake_user
        mock_db.auth.get_user.return_value = auth_get_response
        mock_db.execute.return_value = MagicMock(data={
            "id": str(fake_user.id),
            "full_name": "Test User",
            "username": "testuser",
            "points": 500,
            "avatar_initials": "TU",
            "university_id": None,
        })
        response = client.get(f"{BASE}/me", headers=auth_headers)
        assert response.status_code == 200
