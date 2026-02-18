"""
API Integration tests for FastAPI endpoints.
"""
import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from app.main import app
    return TestClient(app)


class TestRootEndpoint:
    """Tests for root endpoint."""
    
    def test_root_returns_app_info(self, client):
        """Root endpoint returns app information."""
        response = client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert data["app"] == "ChronicAI"
        assert data["status"] == "running"
        assert data["version"] == "1.0.0"
        assert "endpoints" in data


class TestHealthEndpoint:
    """Tests for health endpoint."""
    
    def test_health_endpoint_returns_status(self, client):
        """Health endpoint returns status."""
        response = client.get("/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "api" in data


class TestUploadEndpoints:
    """Tests for upload endpoints."""
    
    def test_upload_text_requires_fields(self, client):
        """Upload text endpoint validates required fields."""
        response = client.post("/upload/text", data={})
        assert response.status_code == 422  # Validation error
    
    def test_upload_document_requires_file(self, client):
        """Upload document endpoint requires file."""
        response = client.post("/upload/document", data={
            "patient_id": "test",
            "record_type": "notes"
        })
        assert response.status_code == 422

    def test_upload_patient_record_image_requires_file(self, client):
        """Upload patient record image endpoint requires file."""
        response = client.post("/upload/patient-record-image", data={
            "patient_id": "test",
            "record_type": "xray"
        })
        assert response.status_code == 422


class TestChatEndpoints:
    """Tests for chat endpoints."""
    
    def test_chat_requires_patient_id(self, client):
        """Chat endpoint validates patient_id format."""
        response = client.post("/chat/", json={
            "patient_id": "invalid-uuid",
            "message": "Test message"
        })
        # Should return 400 for invalid UUID
        assert response.status_code == 400


class TestDoctorEndpoints:
    """Tests for doctor endpoints - require Supabase connection."""

    def test_export_patient_text_rejects_invalid_uuid(self, client):
        """Patient export text endpoint validates patient_id format."""
        response = client.get("/doctor/patients/not-a-uuid/export?format=json")
        assert response.status_code == 400

    def test_export_patient_text_rejects_invalid_format(self, client):
        """Patient export text endpoint validates export format."""
        patient_id = "00000000-0000-0000-0000-000000000000"
        response = client.get(f"/doctor/patients/{patient_id}/export?format=txt")
        assert response.status_code == 422

    def test_export_patient_files_rejects_invalid_uuid(self, client):
        """Patient file export endpoint validates patient_id format."""
        response = client.get("/doctor/patients/not-a-uuid/export/files")
        assert response.status_code == 400
    
    @pytest.mark.skip(reason="Requires Supabase credentials - run with .env configured")
    def test_list_patients_pagination(self, client):
        """List patients supports pagination."""
        response = client.get("/doctor/patients?page=1&page_size=10")
        assert response.status_code == 200
    
    @pytest.mark.skip(reason="Requires Supabase credentials - run with .env configured")
    def test_stats_endpoint(self, client):
        """Stats endpoint exists."""
        response = client.get("/doctor/stats")
        assert response.status_code == 200
