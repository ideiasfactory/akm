"""
Integration tests for project management endpoints.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from main import app
from src.database.models import Base, AKMProject, AKMScope
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
        description="Test project",
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
        AKMScope(scope_name="akm:projects:read", description="Read projects", project_id=test_project.id),
        AKMScope(scope_name="akm:projects:write", description="Write projects", project_id=test_project.id),
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
    """Create an admin API key."""
    repository = APIKeyRepository()
    api_key, plain_key = await repository.create_key(
        test_session,
        project_id=test_project.id,
        name="Admin Key",
        scopes=["akm:*"]
    )
    return plain_key


@pytest.mark.integration
class TestProjectEndpoints:
    """Integration tests for project endpoints"""

    async def test_create_project_success(
        self,
        override_get_session,
        admin_api_key
    ):
        """Test creating a new project"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/akm/projects",
                headers={"X-API-Key": admin_api_key},
                json={
                    "name": "New Project",
                    "description": "Created via API",
                    "owner": "test_owner"
                }
            )
        
        assert response.status_code == 201
        data = response.json()
        
        assert data["name"] == "New Project"
        assert data["description"] == "Created via API"
        assert data["owner"] == "test_owner"
        assert "id" in data

    async def test_list_projects_success(
        self,
        override_get_session,
        admin_api_key,
        test_session
    ):
        """Test listing projects"""
        # Create multiple projects
        for i in range(3):
            project = AKMProject(
                name=f"Project {i}",
                description=f"Description {i}",
                owner="test_user"
            )
            test_session.add(project)
        await test_session.commit()
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/akm/projects",
                headers={"X-API-Key": admin_api_key}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should include the 3 created projects + test fixture project
        assert len(data) >= 3

    async def test_get_project_by_id_success(
        self,
        override_get_session,
        admin_api_key,
        test_project
    ):
        """Test getting project by ID"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/akm/projects/{test_project.id}",
                headers={"X-API-Key": admin_api_key}
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["id"] == test_project.id
        assert data["name"] == test_project.name

    async def test_get_project_by_id_not_found(
        self,
        override_get_session,
        admin_api_key
    ):
        """Test getting non-existent project"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/akm/projects/99999",
                headers={"X-API-Key": admin_api_key}
            )
        
        assert response.status_code == 404

    async def test_update_project_success(
        self,
        override_get_session,
        admin_api_key,
        test_project
    ):
        """Test updating project"""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.put(
                f"/akm/projects/{test_project.id}",
                headers={"X-API-Key": admin_api_key},
                json={
                    "name": "Updated Project",
                    "description": "Updated description"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["name"] == "Updated Project"
        assert data["description"] == "Updated description"

    async def test_delete_project_success(
        self,
        override_get_session,
        admin_api_key,
        test_session
    ):
        """Test deleting project"""
        # Create a project to delete
        project = AKMProject(
            name="Delete Me",
            description="To be deleted",
            owner="test_user"
        )
        test_session.add(project)
        await test_session.commit()
        await test_session.refresh(project)
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.delete(
                f"/akm/projects/{project.id}",
                headers={"X-API-Key": admin_api_key}
            )
        
        assert response.status_code == 204
        
        # Verify deleted
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                f"/akm/projects/{project.id}",
                headers={"X-API-Key": admin_api_key}
            )
        
        assert response.status_code == 404
