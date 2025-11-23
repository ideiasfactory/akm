"""
Unit tests for API Key Repository.
"""

import pytest
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.database.models import Base, AKMAPIKey, AKMProject, AKMScope, AKMAPIKeyScope
from src.database.repositories.api_key_repository import APIKeyRepository


# Test database URL
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
        AKMScope(project_id=test_project.id, scope_name="akm:keys:read", description="Read API keys"),
        AKMScope(project_id=test_project.id, scope_name="akm:keys:write", description="Write API keys"),
        AKMScope(project_id=test_project.id, scope_name="akm:admin:*", description="Admin access"),
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
    return APIKeyRepository()


@pytest.mark.unit
class TestAPIKeyRepository:
    """Test suite for API Key Repository"""

    async def test_hash_key(self, repository):
        """Test key hashing is consistent"""
        key = "test_key_123"
        hash1 = repository.hash_key(key)
        hash2 = repository.hash_key(key)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest length
        assert hash1 != key

    async def test_generate_key(self, repository):
        """Test key generation"""
        key = repository.generate_key()
        
        assert key.startswith("akm_")
        assert len(key) > 10
        
        # Test uniqueness
        key2 = repository.generate_key()
        assert key != key2

    async def test_generate_key_custom_prefix(self, repository):
        """Test key generation with custom prefix"""
        key = repository.generate_key(prefix="custom")
        
        assert key.startswith("custom_")

    async def test_create_key(self, repository, test_session, test_project, test_scopes):
        """Test creating an API key"""
        api_key, plain_key = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Test Key",
            scopes=["akm:keys:read"],
            description="Test description"
        )
        
        assert api_key is not None
        assert api_key.id is not None
        assert api_key.name == "Test Key"
        assert api_key.description == "Test description"
        assert api_key.is_active is True
        assert plain_key is not None
        assert plain_key.startswith("akm_")

    async def test_create_key_with_multiple_scopes(self, repository, test_session, test_project, test_scopes):
        """Test creating an API key with multiple scopes"""
        api_key, plain_key = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Multi-Scope Key",
            scopes=["akm:keys:read", "akm:keys:write"],
            description="Key with multiple scopes"
        )
        
        assert api_key is not None
        assert plain_key is not None
        # Verify by reloading
        reloaded = await repository.get_by_id(test_session, api_key.id)
        assert len(reloaded.scopes) == 2

    async def test_create_key_with_expiration(self, repository, test_session, test_project, test_scopes):
        """Test creating an API key with expiration"""
        expires_at = datetime.utcnow() + timedelta(days=30)
        
        api_key, _ = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Expiring Key",
            scopes=["akm:keys:read"],
            expires_at=expires_at
        )
        
        assert api_key.expires_at is not None
        assert api_key.expires_at.date() == expires_at.date()

    async def test_create_key_invalid_scope(self, repository, test_session, test_project, test_scopes):
        """Test creating an API key with invalid scope raises error"""
        with pytest.raises(ValueError, match="Scope 'invalid:scope' not found"):
            await repository.create_key(
                test_session,
                project_id=test_project.id,
                name="Invalid Scope Key",
                scopes=["invalid:scope"]
            )

    async def test_validate_key_success(self, repository, test_session, test_project, test_scopes):
        """Test validating a valid API key"""
        # Create key
        api_key, plain_key = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Valid Key",
            scopes=["akm:keys:read"]
        )
        
        # Validate
        validated = await repository.validate_key(test_session, plain_key)
        
        assert validated is not None
        assert validated.id == api_key.id
        assert validated.name == "Valid Key"
        assert validated.last_used_at is not None
        assert validated.request_count == 1

    async def test_validate_key_increments_counter(self, repository, test_session, test_project, test_scopes):
        """Test that validating a key increments request counter"""
        api_key, plain_key = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Counter Key",
            scopes=["akm:keys:read"]
        )
        
        # Validate multiple times
        await repository.validate_key(test_session, plain_key)
        await repository.validate_key(test_session, plain_key)
        await repository.validate_key(test_session, plain_key)
        
        # Check counter
        reloaded = await repository.get_by_id(test_session, api_key.id, load_scopes=False)
        assert reloaded.request_count == 3

    async def test_validate_key_invalid(self, repository, test_session):
        """Test validating an invalid API key returns None"""
        validated = await repository.validate_key(test_session, "invalid_key_123")
        assert validated is None

    async def test_validate_key_inactive(self, repository, test_session, test_project, test_scopes):
        """Test validating an inactive key returns None"""
        api_key, plain_key = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Inactive Key",
            scopes=["akm:keys:read"]
        )
        
        # Revoke key
        await repository.revoke_key(test_session, api_key.id)
        
        # Try to validate
        validated = await repository.validate_key(test_session, plain_key)
        assert validated is None

    async def test_validate_key_expired(self, repository, test_session, test_project, test_scopes):
        """Test validating an expired key returns None"""
        expires_at = datetime.utcnow() - timedelta(days=1)  # Expired yesterday
        
        api_key, plain_key = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Expired Key",
            scopes=["akm:keys:read"],
            expires_at=expires_at
        )
        
        validated = await repository.validate_key(test_session, plain_key)
        assert validated is None

    async def test_get_by_id(self, repository, test_session, test_project, test_scopes):
        """Test getting API key by ID"""
        api_key, _ = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Get By ID Key",
            scopes=["akm:keys:read"]
        )
        
        retrieved = await repository.get_by_id(test_session, api_key.id)
        
        assert retrieved is not None
        assert retrieved.id == api_key.id
        assert retrieved.name == "Get By ID Key"

    async def test_get_by_id_not_found(self, repository, test_session):
        """Test getting non-existent API key returns None"""
        retrieved = await repository.get_by_id(test_session, 99999)
        assert retrieved is None

    async def test_get_by_name(self, repository, test_session, test_project, test_scopes):
        """Test getting API key by name"""
        await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Unique Name Key",
            scopes=["akm:keys:read"]
        )
        
        retrieved = await repository.get_by_name(test_session, "Unique Name Key")
        
        assert retrieved is not None
        assert retrieved.name == "Unique Name Key"

    async def test_list_all(self, repository, test_session, test_project, test_scopes):
        """Test listing all API keys"""
        # Create multiple keys
        for i in range(5):
            await repository.create_key(
                test_session,
                project_id=test_project.id,
                name=f"Key {i}",
                scopes=["akm:keys:read"]
            )
        
        keys = await repository.list_all(test_session)
        
        assert len(keys) == 5

    async def test_list_all_with_pagination(self, repository, test_session, test_project, test_scopes):
        """Test listing API keys with pagination"""
        # Create multiple keys
        for i in range(10):
            await repository.create_key(
                test_session,
                project_id=test_project.id,
                name=f"Key {i}",
                scopes=["akm:keys:read"]
            )
        
        # Get first page
        page1 = await repository.list_all(test_session, skip=0, limit=5)
        assert len(page1) == 5
        
        # Get second page
        page2 = await repository.list_all(test_session, skip=5, limit=5)
        assert len(page2) == 5
        
        # Ensure different keys
        page1_ids = {k.id for k in page1}
        page2_ids = {k.id for k in page2}
        assert page1_ids.isdisjoint(page2_ids)

    async def test_list_all_active_only(self, repository, test_session, test_project, test_scopes):
        """Test listing only active API keys"""
        # Create active keys
        for i in range(3):
            await repository.create_key(
                test_session,
                project_id=test_project.id,
                name=f"Active Key {i}",
                scopes=["akm:keys:read"]
            )
        
        # Create and revoke keys
        for i in range(2):
            api_key, _ = await repository.create_key(
                test_session,
                project_id=test_project.id,
                name=f"Revoked Key {i}",
                scopes=["akm:keys:read"]
            )
            await repository.revoke_key(test_session, api_key.id)
        
        # List active only
        active_keys = await repository.list_all(test_session, active_only=True)
        assert len(active_keys) == 3
        
        # List all
        all_keys = await repository.list_all(test_session, active_only=False)
        assert len(all_keys) == 5

    async def test_update_key(self, repository, test_session, test_project, test_scopes):
        """Test updating API key metadata"""
        api_key, _ = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Original Name",
            scopes=["akm:keys:read"],
            description="Original description"
        )
        
        updated = await repository.update_key(
            test_session,
            api_key.id,
            name="Updated Name",
            description="Updated description"
        )
        
        assert updated is not None
        assert updated.name == "Updated Name"
        assert updated.description == "Updated description"

    async def test_update_key_partial(self, repository, test_session, test_project, test_scopes):
        """Test partial update of API key"""
        api_key, _ = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Original Name",
            scopes=["akm:keys:read"],
            description="Original description"
        )
        
        # Update only name
        updated = await repository.update_key(
            test_session,
            api_key.id,
            name="New Name"
        )
        
        assert updated.name == "New Name"
        assert updated.description == "Original description"

    async def test_add_scopes(self, repository, test_session, test_project, test_scopes):
        """Test adding scopes to an API key"""
        api_key, _ = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Scope Test Key",
            scopes=["akm:keys:read"]
        )
        
        # Add another scope
        success = await repository.add_scopes(
            test_session,
            api_key.id,
            ["akm:keys:write"]
        )
        
        assert success is True

    async def test_add_scopes_duplicate(self, repository, test_session, test_project, test_scopes):
        """Test adding duplicate scopes doesn't create duplicates"""
        api_key, _ = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Duplicate Scope Key",
            scopes=["akm:keys:read"]
        )
        
        # Try to add same scope again
        await repository.add_scopes(test_session, api_key.id, ["akm:keys:read"])
        
        # Verify only one scope
        reloaded = await repository.get_by_id(test_session, api_key.id)
        assert len(reloaded.scopes) == 1

    async def test_remove_scopes(self, repository, test_session, test_project, test_scopes):
        """Test removing scopes from an API key"""
        api_key, _ = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Remove Scope Key",
            scopes=["akm:keys:read", "akm:keys:write"]
        )
        
        # Remove scope
        success = await repository.remove_scopes(
            test_session,
            api_key.id,
            ["akm:keys:write"]
        )
        
        assert success is True
        
        # Verify
        reloaded = await repository.get_by_id(test_session, api_key.id)
        scope_names = {s.scope.scope_name for s in reloaded.scopes}
        assert scope_names == {"akm:keys:read"}

    async def test_revoke_key(self, repository, test_session, test_project, test_scopes):
        """Test revoking an API key"""
        api_key, plain_key = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Revoke Test Key",
            scopes=["akm:keys:read"]
        )
        
        # Revoke
        success = await repository.revoke_key(test_session, api_key.id)
        assert success is True
        
        # Verify inactive
        reloaded = await repository.get_by_id(test_session, api_key.id, load_scopes=False)
        assert reloaded.is_active is False
        
        # Verify can't validate
        validated = await repository.validate_key(test_session, plain_key)
        assert validated is None

    async def test_delete_key(self, repository, test_session, test_project, test_scopes):
        """Test permanently deleting an API key"""
        api_key, _ = await repository.create_key(
            test_session,
            project_id=test_project.id,
            name="Delete Test Key",
            scopes=["akm:keys:read"]
        )
        
        key_id = api_key.id
        
        # Delete
        success = await repository.delete_key(test_session, key_id)
        assert success is True
        
        # Verify deleted
        reloaded = await repository.get_by_id(test_session, key_id, load_scopes=False)
        assert reloaded is None
