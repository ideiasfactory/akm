"""
Unit tests for Scope Repository.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.database.models import Base, AKMScope, AKMProject
from src.database.repositories.scope_repository import ScopeRepository


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
async def test_project(test_session: AsyncSession):
    """Create a test project."""
    project = AKMProject(
        name="Test Project",
        prefix="test",
        description="Test project for unit tests"
    )
    test_session.add(project)
    await test_session.commit()
    await test_session.refresh(project)
    return project


@pytest.fixture
async def test_scopes(test_session: AsyncSession, test_project: AKMProject):
    """Create test scopes."""
    scopes = [
        AKMScope(project_id=test_project.id, scope_name="test:read", description="Read access"),
        AKMScope(project_id=test_project.id, scope_name="test:write", description="Write access"),
        AKMScope(project_id=test_project.id, scope_name="test:admin", description="Admin access"),
    ]
    for scope in scopes:
        test_session.add(scope)
    await test_session.commit()
    
    for scope in scopes:
        await test_session.refresh(scope)
    
    return scopes


@pytest.fixture
def repository():
    """Create repository instance."""
    return ScopeRepository()


@pytest.mark.unit
class TestScopeRepository:
    """Test suite for Scope Repository"""

    async def test_get_by_name(self, repository, test_session, test_scopes):
        """Test getting scope by name"""
        scope = await repository.get_by_name(test_session, "test:read")
        
        assert scope is not None
        assert scope.scope_name == "test:read"
        assert scope.description == "Read access"

    async def test_get_by_name_not_found(self, repository, test_session, test_scopes):
        """Test getting non-existent scope returns None"""
        scope = await repository.get_by_name(test_session, "nonexistent:scope")
        assert scope is None

    async def test_list_all(self, repository, test_session, test_scopes):
        """Test listing all scopes"""
        scopes = await repository.list_all(test_session)
        
        assert len(scopes) == 3
        scope_names = {s.scope_name for s in scopes}
        assert scope_names == {"test:read", "test:write", "test:admin"}

    async def test_bulk_exists_all_valid(self, repository, test_session, test_scopes):
        """Test checking multiple valid scopes"""
        result = await repository.bulk_exists(
            test_session,
            ["test:read", "test:write"]
        )
        
        assert result == {"test:read": True, "test:write": True}

    async def test_bulk_exists_mixed(self, repository, test_session, test_scopes):
        """Test checking mix of valid and invalid scopes"""
        result = await repository.bulk_exists(
            test_session,
            ["test:read", "invalid:scope", "test:admin"]
        )
        
        assert result == {
            "test:read": True,
            "invalid:scope": False,
            "test:admin": True
        }

    async def test_bulk_exists_all_invalid(self, repository, test_session, test_scopes):
        """Test checking all invalid scopes"""
        result = await repository.bulk_exists(
            test_session,
            ["invalid:one", "invalid:two"]
        )
        
        assert result == {"invalid:one": False, "invalid:two": False}

    async def test_create_scope(self, repository, test_session, test_project):
        """Test creating a new scope"""
        scope = await repository.create(
            test_session,
            project_id=test_project.id,
            scope_name="new:scope",
            description="New test scope"
        )
        
        assert scope is not None
        assert scope.id is not None
        assert scope.scope_name == "new:scope"
        assert scope.description == "New test scope"

    async def test_create_scope_duplicate(self, repository, test_session, test_scopes, test_project):
        """Test creating duplicate scope raises error"""
        with pytest.raises(Exception):  # SQLAlchemy IntegrityError
            await repository.create(
                test_session,
                project_id=test_project.id,
                scope_name="test:read",
                description="Duplicate scope"
            )
