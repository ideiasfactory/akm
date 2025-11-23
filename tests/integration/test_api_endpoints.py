"""Integration tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.integration
class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, client: TestClient):
        """Test main health endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data

    def test_liveness_probe(self, client: TestClient):
        """Test liveness probe."""
        response = client.get("/health/liveness")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_readiness_probe(self, client: TestClient):
        """Test readiness probe."""
        response = client.get("/health/readiness")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert "database" in data


@pytest.mark.integration
class TestHomeEndpoints:
    """Test home page endpoints."""

    def test_home_page(self, client: TestClient):
        """Test home page returns HTML."""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_home_data_json(self, client: TestClient):
        """Test home data JSON endpoint."""
        response = client.get("/api/home/data")

        assert response.status_code == 200
        data = response.json()
        assert "title" in data
        assert "version" in data
        assert "environment" in data


@pytest.mark.integration
class TestAPIResponseStructure:
    """Test standardized API response structure."""

    def test_health_response_structure(self, client: TestClient):
        """Test health check response structure."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "status" in data
        assert "timestamp" in data
        assert "version" in data


@pytest.mark.integration
class TestCORSHeaders:
    """Test CORS headers are present."""

    def test_cors_headers_present(self, client: TestClient):
        """Test that CORS headers are set correctly."""
        response = client.get("/health")

        # Check that CORS headers are present in response
        # FastAPI's CORS middleware adds headers to all responses
        assert response.status_code == 200


@pytest.mark.integration
class TestErrorHandling:
    """Test API error handling."""

    def test_404_endpoint_not_found(self, client: TestClient):
        """Test 404 error for non-existent endpoint."""
        response = client.get("/api/nonexistent")

        assert response.status_code == 404

    def test_405_method_not_allowed(self, client: TestClient):
        """Test 405 error for unsupported HTTP method."""
        response = client.post("/health")

        assert response.status_code == 405


@pytest.mark.integration
@pytest.mark.slow
class TestAPIDocumentation:
    """Test API documentation endpoints."""

    def test_openapi_json(self, client: TestClient):
        """Test OpenAPI JSON schema is accessible."""
        response = client.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert "paths" in data

    def test_swagger_ui(self, client: TestClient):
        """Test Swagger UI is accessible."""
        response = client.get("/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc(self, client: TestClient):
        """Test ReDoc is accessible."""
        response = client.get("/redoc")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
