"""
test_centers.py
"""
from unittest.mock import MagicMock
import pytest

BASE = "/api/v1/centers"

CENTER_FIXTURE = {
    "id": "center-001",
    "name": "Centro Norte",
    "district": "Miraflores",
    "address": "Av. Principal 123",
    "lat": -12.1234,
    "lng": -77.0234,
    "status": "disponible",
    "accepted_materials": ["Plástico", "Papel", "Vidrio"],
    "hours": "Lun-Sab 8am-6pm",
    "wait_minutes": 5,
    "capacity": 80,
    "rating": 4.5,
}

class TestGetAllCenters:
    def test_returns_all_centers(self, client, mock_db):
        mock_db.execute.return_value = MagicMock(data=[CENTER_FIXTURE])
        response = client.get(f"{BASE}/")
        assert response.status_code == 200

    def test_returns_empty_list(self, client, mock_db):
        mock_db.execute.return_value = MagicMock(data=[])
        response = client.get(f"{BASE}/")
        assert response.status_code == 200

class TestGetAvailableCenters:
    def test_returns_available_centers(self, client, mock_db):
        mock_db.execute.return_value = MagicMock(data=[CENTER_FIXTURE])
        response = client.get(f"{BASE}/available")
        assert response.status_code == 200

    def test_returns_empty_when_all_closed(self, client, mock_db):
        mock_db.execute.return_value = MagicMock(data=[])
        response = client.get(f"{BASE}/available")
        assert response.status_code == 200

class TestSearchCenters:
    def test_search_with_campus_param(self, client, mock_db):
        mock_db.execute.return_value = MagicMock(data=[CENTER_FIXTURE])
        response = client.get(f"{BASE}/search?campus=miraflores")
        assert response.status_code == 200

    def test_search_with_material_param(self, client, mock_db):
        mock_db.execute.return_value = MagicMock(data=[CENTER_FIXTURE])
        response = client.get(f"{BASE}/search?material=Papel")
        assert response.status_code == 200

    def test_search_with_no_params(self, client, mock_db):
        mock_db.execute.return_value = MagicMock(data=[CENTER_FIXTURE])
        response = client.get(f"{BASE}/search")
        assert response.status_code == 200

    def test_search_with_only_active(self, client, mock_db):
        mock_db.execute.return_value = MagicMock(data=[])
        response = client.get(f"{BASE}/search?only_active=true")
        assert response.status_code == 200

class TestGetCentersByMaterial:
    def test_returns_centers_accepting_material(self, client, mock_db):
        mock_db.execute.return_value = MagicMock(data=[CENTER_FIXTURE])
        response = client.get(f"{BASE}/by-material?material=Vidrio")
        assert response.status_code == 200

    def test_requires_material_param(self, client, mock_db):
        response = client.get(f"{BASE}/by-material")
        assert response.status_code == 422

class TestGetCenterById:
    def test_returns_center_by_id(self, client, mock_db):
        mock_db.execute.return_value = MagicMock(data=CENTER_FIXTURE)
        response = client.get(f"{BASE}/center-001")
        assert response.status_code == 200

    def test_returns_404_when_center_not_found(self, client, mock_db):
        mock_db.execute.return_value = MagicMock(data=None)
        response = client.get(f"{BASE}/nonexistent-id")
        assert response.status_code == 404
