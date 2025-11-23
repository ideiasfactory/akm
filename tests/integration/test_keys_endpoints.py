"""
Integration tests for API Key management endpoints.
"""

import pytest
from datetime import datetime, timedelta
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi import FastAPI

from main import app
from src.database.models import Base, AKMAPIKey, AKMProject, AKMScope
from src.database.connection import get_session
from src.database.repositories.api_key_repository import APIKeyRepository


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Create test database session."""
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        yield session


@pytest.fixture
async def override_get_session(test_engine):
    """Override get_session dependency."""
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    
    async def _override():
        async with async_session() as session:
            yield session
    
    app.dependency_overrides[get_session] = _override
    yield
    app.dependency_overrides.clear()


@pytest.fixture
async def test_project(test_session: AsyncSession):
    """Create a test project."""
    project = AKMProject(
        name="Test Project",
        description="Test project for integration tests",
        prefix="test"
    )
    test_session.add(project)
    await test_session.commit()
    await test_session.refresh(project)
    return project


@pytest.fixture
async def test_scopes(test_session: AsyncSession, test_project: AKMProject):
    """Create test scopes."""
    scopes = [
        AKMScope(scope_name="akm:keys:read", description="Read API keys", project_id=test_project.id),
        AKMScope(scope_name="akm:keys:write", description="Write API keys", project_id=test_project.id),
        AKMScope(scope_name="akm:admin:*", description="Admin access", project_id=test_project.id),
        AKMScope(scope_name="akm:*", description="Full access", project_id=test_project.id),
    ]
    for scope in scopes:
        test_session.add(scope)
    await test_session.commit()
    
    for scope in scopes:
        await test_session.refresh(scope)
    
    return scopes


@pytest.fixture
async def admin_api_key(test_session: AsyncSession, test_project, test_scopes):
    """Create an admin API key for testing."""
    repository = APIKeyRepository()
    api_key, plain_key = await repository.create_key(
        test_session,
        project_id=test_project.id,
        name="Admin Test Key",
        scopes=["akm:*"],
        description="Admin key for testing"
    )
    return plain_key


@pytest.fixture
async def read_only_api_key(test_session: AsyncSession, test_project, test_scopes):
    """Create a read-only API key for testing."""
    repository = APIKeyRepository()
    api_key, plain_key = await repository.create_key(
        test_session,
        project_id=test_project.id,
        name="Read-Only Test Key",
        scopes=["akm:keys:read"],
        description="Read-only key for testing"
    )
    return plain_key


@pytest.mark.integration
class TestAPIKeyEndpoints:
    """Integration tests for API Key endpoints"""

    async def test_create_api_key_success(
        self,
        override_get_session,
        admin_api_key,
        test_project
    ):
        """Test creating a new API key"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/akm/keys",
                headers={"X-API-Key": admin_api_key},
                json={
                    "project_id": test_project.id,
                    "name": "New Test Key",
                    "scopes": ["akm:keys:read"],
                    "description": "Created via API"
                }
            )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["name"] == "New Test Key"
        assert data["description"] == "Created via API"
        assert "key" in data
        assert data["key"].startswith("akm_")
        assert "akm:keys:read" in data["scopes"]

    async def test_create_api_key_invalid_scope(
        self,
        override_get_session,
        admin_api_key,
        test_project
    ):
        """Test creating API key with invalid scope"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/akm/keys",
                headers={"X-API-Key": admin_api_key},
                json={
                    "project_id": test_project.id,
                    "name": "Invalid Scope Key",
                    "scopes": ["invalid:scope"],
                    "description": "Should fail"
                }
            )
        
        assert response.status_code == 400
        assert "Invalid scopes" in response.json()["detail"]

    async def test_create_api_key_without_permission(
        self,
        override_get_session,
        read_only_api_key,
        test_project
    ):
        """Test creating API key without write permission"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/akm/keys",
                headers={"X-API-Key": read_only_api_key},
                json={
                    "project_id": test_project.id,
                    "name": "Unauthorized Key",
                    "scopes": ["akm:keys:read"]
                }
            )
        
        assert response.status_code == 403

    async def test_create_api_key_without_auth(
        self,
        override_get_session,
        test_project
    ):
        """Test creating API key without authentication"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/akm/keys",
                json={
                    "project_id": test_project.id,
                    "name": "Unauthorized Key",
                    "scopes": ["akm:keys:read"]
                }
            )
        
        assert response.status_code == 401

    async def test_list_api_keys_success(
        self,
        override_get_session,
        admin_api_key,
        test_session,
        test_project,
        test_scopes
    ):
        """Test listing API keys"""
        # Create some keys
        repository = APIKeyRepository()
        for i in range(3):
            await repository.create_key(
                test_session,
                project_id=test_project.id,
                name=f"List Test Key {i}",
                scopes=["akm:keys:read"]
            )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/akm/keys",
                headers={"X-API-Key": admin_api_key}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include the 3 created keys + admin key
        assert len(data) >= 3

    async def test_list_api_keys_with_pagination(
        self,
        override_get_session,
        admin_api_key,
        test_session,
        test_project,
        test_scopes
    ):
        """Test listing API keys with pagination"""
        # Create multiple keys
        repository = APIKeyRepository()
        for i in range(10):
            await repository.create_key(
                test_session,
                project_id=test_project.id,
                name=f"Pagination Key {i}",
                scopes=["akm:keys:read"]
            )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Get first page
            response1 = await client.get(
                "/akm/keys?skip=0&limit=5",
                headers={"X-API-Key": admin_api_key}
            )
            
            # Get second page
            response2 = await client.get(
                "/akm/keys?skip=5&limit=5",
                headers={"X-API-Key": admin_api_key}
            )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        page1 = response1.json()
        page2 = response2.json()
        
        assert len(page1) == 5
        assert len(page2) >= 5
        
        # Ensure different keys
        page1_ids = {k["id"] for k in page1}
        page2_ids = {k["id"] for k in page2}
        assert page1_ids.isdisjoint(page2_ids)

    async def test_get_api_key_by_id_success(
        self,
        override_get_session,
        admin_api_key,
        test_session,
        test_project,
        test_scopes
    ):
        """Test getting API key by ID"""
        # Create a key
        repository = APIKeyRepository()
        api_key, _ = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Get By ID Key",
            scopes=["akm:keys:read"]
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/akm/keys/{api_key.id}",
                headers={"X-API-Key": admin_api_key}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == api_key.id
        assert data["name"] == "Get By ID Key"
        assert "akm:keys:read" in data["scopes"]

    async def test_get_api_key_by_id_not_found(
        self,
        override_get_session,
        admin_api_key
    ):
        """Test getting non-existent API key"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/akm/keys/99999",
                headers={"X-API-Key": admin_api_key}
            )
        
        assert response.status_code == 404

    async def test_update_api_key_success(
        self,
        override_get_session,
        admin_api_key,
        test_session,
        test_project,
        test_scopes
    ):
        """Test updating API key"""
        # Create a key
        repository = APIKeyRepository()
        api_key, _ = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Original Name",
            scopes=["akm:keys:read"],
            description="Original description"
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/akm/keys/{api_key.id}",
                headers={"X-API-Key": admin_api_key},
                json={
                    "name": "Updated Name",
                    "description": "Updated description"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated description"

    async def test_update_api_key_scopes_success(
        self,
        override_get_session,
        admin_api_key,
        test_session,
        test_project,
        test_scopes
    ):
        """Test updating API key scopes"""
        # Create a key
        repository = APIKeyRepository()
        api_key, _ = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Scope Update Key",
            scopes=["akm:keys:read"]
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/akm/keys/{api_key.id}/scopes",
                headers={"X-API-Key": admin_api_key},
                json={
                    "scopes": ["akm:keys:read", "akm:keys:write"]
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "akm:keys:read" in data["scopes"]
        assert "akm:keys:write" in data["scopes"]

    async def test_revoke_api_key_success(
        self,
        override_get_session,
        admin_api_key,
        test_session,
        test_project,
        test_scopes
    ):
        """Test revoking API key"""
        # Create a key
        repository = APIKeyRepository()
        api_key, plain_key = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Revoke Test Key",
            scopes=["akm:keys:read"]
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Revoke key
            response = await client.post(
                f"/akm/keys/{api_key.id}/revoke",
                headers={"X-API-Key": admin_api_key}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
        
        # Try to use revoked key
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/akm/keys",
                headers={"X-API-Key": plain_key}
            )
        
        assert response.status_code == 401

    async def test_delete_api_key_success(
        self,
        override_get_session,
        admin_api_key,
        test_session,
        test_project,
        test_scopes
    ):
        """Test deleting API key"""
        # Create a key
        repository = APIKeyRepository()
        api_key, _ = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Delete Test Key",
            scopes=["akm:keys:read"]
        )
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete(
                f"/akm/keys/{api_key.id}",
                headers={"X-API-Key": admin_api_key}
            )
        
        assert response.status_code == 204
        
        # Verify deleted
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/akm/keys/{api_key.id}",
                headers={"X-API-Key": admin_api_key}
            )
        
        assert response.status_code == 404


@pytest.mark.integration
class TestHealthEndpoints:
    """Integration tests for health check endpoints"""

    async def test_health_check(self, override_get_session):
        """Test basic health check"""
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "healthy"
        assert "version" in data
        assert "database" in data

    async def test_health_ready(self, override_get_session):
        """Test readiness check"""
        from httpx import ASGITransport
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/health/ready")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["ready"] is True
        assert "checks" in data
