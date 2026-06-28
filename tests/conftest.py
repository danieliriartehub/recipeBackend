"""
conftest.py – Fixtures compartidos para todos los tests del backend.
"""
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.core.supabase import get_supabase_admin_client, get_supabase_client
from app.core.dependencies import get_current_user

class FakeUser:
    id = "00000000-0000-0000-0000-000000000001"
    email = "test@recipe.app"
    user_metadata = {"full_name": "Test User"}
    email_confirmed_at = "2024-01-01T00:00:00Z"

def override_get_current_user():
    return FakeUser()

def build_supabase_mock() -> MagicMock:
    mock = MagicMock()
    mock.table.return_value = mock
    mock.select.return_value = mock
    mock.insert.return_value = mock
    mock.update.return_value = mock
    mock.delete.return_value = mock
    mock.upsert.return_value = mock
    mock.eq.return_value = mock
    mock.neq.return_value = mock
    mock.in_.return_value = mock
    mock.not_.in_.return_value = mock
    mock.is_.return_value = mock
    mock.ilike.return_value = mock
    mock.contains.return_value = mock
    mock.lte.return_value = mock
    mock.gte.return_value = mock
    mock.lt.return_value = mock
    mock.gt.return_value = mock
    mock.or_.return_value = mock
    mock.order.return_value = mock
    mock.limit.return_value = mock
    mock.range.return_value = mock
    mock.single.return_value = mock
    mock.execute.return_value = MagicMock(data=None)
    return mock

@pytest.fixture
def mock_db() -> MagicMock:
    mock = build_supabase_mock()
    app.dependency_overrides[get_supabase_admin_client] = lambda: mock
    app.dependency_overrides[get_supabase_client] = lambda: mock
    app.dependency_overrides[get_current_user] = override_get_current_user
    yield mock
    app.dependency_overrides.clear()

@pytest.fixture
def client(mock_db) -> TestClient:
    return TestClient(app)

@pytest.fixture
def auth_headers() -> dict:
    return {"Authorization": "Bearer fake-test-token"}

@pytest.fixture
def user_id() -> str:
    return "00000000-0000-0000-0000-000000000001"
