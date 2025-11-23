"""Pytest configuration and shared fixtures."""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from main import app
from src.database.models import Base, AKMAPIKey, AKMProject, AKMScope
from src.database.repositories.api_key_repository import APIKeyRepository


# Test database URL (use in-memory SQLite for tests)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture(scope="function")
async def api_key_repository(test_session: AsyncSession) -> APIKeyRepository:
    """Create API key repository for testing."""
    return APIKeyRepository(test_session)


@pytest.fixture(scope="function")
async def test_api_key(api_key_repository: APIKeyRepository) -> tuple[str, AKMAPIKey]:
    """Create a test API key.

    Returns:
        tuple: (api_key_string, api_key_record)
    """
    import secrets

    api_key = secrets.token_urlsafe(32)
    record = await api_key_repository.create_key(
        key=api_key, name="Test Key", description="Test API key for unit tests"
    )
    return api_key, record


@pytest.fixture(scope="function")
def client(test_engine) -> Generator:
    """Create FastAPI test client with test database session."""
    from src.database.connection import get_session

    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_session():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_client() -> AsyncGenerator:
    """Create async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture(scope="function")
def mock_env_vars(monkeypatch):
    """Set up mock environment variables for testing."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("API_VERSION", "1.0.0-test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("DATABASE_URL", TEST_DATABASE_URL)


@pytest.fixture(scope="function")
def invalid_api_key() -> str:
    """Return an invalid API key for testing auth failures."""
    return "invalid_key_that_does_not_exist_in_database"


# Markers
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "auth: mark test as authentication related")

