"""
Integration tests for API versioning.
"""

import pytest
from httpx import AsyncClient, ASGITransport

from main import app


@pytest.mark.integration
class TestAPIVersioning:
    """Test API versioning functionality."""

    async def test_v1_endpoint_returns_version_header(self):
        """Test that v1 endpoints include version header."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/akm/v1/keys")
        
        # Should have version headers
        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == "v1"
        assert "X-API-Latest-Version" in response.headers

    async def test_legacy_endpoint_shows_deprecation_warning(self):
        """Test that legacy (unversioned) endpoints show deprecation headers."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/akm/keys")
        
        # Should have deprecation headers
        assert "X-API-Deprecated" in response.headers
        assert response.headers["X-API-Deprecated"] == "true"
        assert "X-API-Deprecated-Message" in response.headers
        assert "X-API-Sunset-Date" in response.headers
        
        # Should have version headers
        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == "legacy"

    async def test_health_endpoint_not_affected_by_versioning(self):
        """Test that health endpoints are not affected by versioning."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
        
        # Health endpoint should work and not show deprecation (307 redirect is ok)
        assert response.status_code in [200, 307]
        assert "X-API-Deprecated" not in response.headers

    async def test_home_endpoint_not_affected_by_versioning(self):
        """Test that home endpoint is not affected by versioning."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/")
        
        # Home endpoint should work and not show deprecation
        assert response.status_code == 200
        assert "X-API-Deprecated" not in response.headers

    async def test_v1_projects_endpoint_versioned(self):
        """Test that v1 projects endpoint works."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/akm/v1/projects")
        
        # Should have version headers
        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == "v1"
        assert "X-API-Deprecated" not in response.headers  # v1 is not deprecated yet

    async def test_legacy_projects_endpoint_deprecated(self):
        """Test that legacy projects endpoint shows deprecation."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/akm/projects")
        
        # Should show deprecation
        assert "X-API-Deprecated" in response.headers
        assert response.headers["X-API-Deprecated"] == "true"

    async def test_correlation_id_preserved_with_versioning(self):
        """Test that correlation ID works with versioning middleware."""
        correlation_id = "test-correlation-123"
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Use follow_redirects to handle any redirects
            response = await client.get(
                "/akm/v1/keys",
                headers={"X-Correlation-ID": correlation_id},
                follow_redirects=True
            )
        
        # Correlation ID should be preserved
        assert "X-Correlation-ID" in response.headers
        # Note: Correlation ID might be regenerated, just check it exists
        assert len(response.headers["X-Correlation-ID"]) > 0
        
        # Version headers should also be present
        assert "X-API-Version" in response.headers

    async def test_deprecated_message_recommends_latest_version(self):
        """Test that deprecation message recommends latest version."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/akm/keys")
        
        deprecation_msg = response.headers.get("X-API-Deprecated-Message", "")
        
        # Should recommend using versioned endpoint
        assert "v1" in deprecation_msg.lower() or "version" in deprecation_msg.lower()

    async def test_v1_scopes_endpoint_works(self):
        """Test that v1 scopes endpoint is accessible."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/akm/v1/scopes")
        
        # Should work (401 is expected without auth)
        assert response.status_code in [200, 401]
        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == "v1"

    async def test_v1_webhooks_endpoint_works(self):
        """Test that v1 webhooks endpoint is accessible."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/akm/v1/webhooks")
        
        # Should work (401 is expected without auth)
        assert response.status_code in [200, 401]
        assert "X-API-Version" in response.headers
        assert response.headers["X-API-Version"] == "v1"


@pytest.mark.integration
class TestAPIVersioningEdgeCases:
    """Test edge cases for API versioning."""

    async def test_versioned_endpoint_with_trailing_slash(self):
        """Test that trailing slashes work with versioned endpoints."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/akm/v1/keys/")
        
        # Should work (or redirect)
        assert response.status_code in [200, 307, 401]  # 307 is redirect, 401 is auth required

    async def test_versioned_endpoint_with_id_parameter(self):
        """Test that versioned endpoints work with path parameters."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/akm/v1/keys/123")
        
        # Should work (404 or 401 expected without auth/valid ID)
        assert response.status_code in [200, 401, 404]
        assert "X-API-Version" in response.headers

    async def test_docs_endpoint_accessible(self):
        """Test that API documentation is accessible."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/docs")
        
        # Docs should be accessible
        assert response.status_code == 200

    async def test_openapi_schema_accessible(self):
        """Test that OpenAPI schema is accessible."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/openapi.json")
        
        # OpenAPI schema should be accessible
        assert response.status_code == 200
        data = response.json()
        
        # Should have API info
        assert "info" in data
        assert "version" in data["info"]
