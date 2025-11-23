# Test Suite Documentation

## Overview

This test suite provides comprehensive coverage for the API Key Management system, including unit tests for individual components and integration tests for end-to-end functionality.

## Test Structure

```
tests/
├── unit/                           # Unit tests (fast, isolated)
│   ├── test_api_key_repository.py  # Repository CRUD operations
│   ├── test_scope_repository.py    # Scope management
│   ├── test_auth_middleware.py     # Authentication & authorization
│   ├── test_auth.py               # (existing) Auth utilities
│   └── test_models.py             # (existing) Model validation
│
├── integration/                    # Integration tests (uses test database)
│   ├── test_keys_endpoints.py      # API key management endpoints
│   ├── test_projects_endpoints.py  # Project management endpoints
│   └── test_api_endpoints.py      # (existing) General API tests
│
└── conftest.py                     # Shared fixtures and configuration
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Only Unit Tests (fast)
```bash
pytest -m unit
```

### Run Only Integration Tests
```bash
pytest -m integration
```

### Run Specific Test File
```bash
pytest tests/unit/test_api_key_repository.py
```

### Run Specific Test Class
```bash
pytest tests/unit/test_api_key_repository.py::TestAPIKeyRepository
```

### Run Specific Test
```bash
pytest tests/unit/test_api_key_repository.py::TestAPIKeyRepository::test_create_key
```

### Run with Coverage Report
```bash
pytest --cov=src --cov-report=html
```

Then open `htmlcov/index.html` in your browser.

### Run Tests in Parallel (faster)
```bash
pytest -n auto
```

## Test Categories

### Unit Tests (`@pytest.mark.unit`)

Fast, isolated tests that test individual components without external dependencies.

**Coverage:**
- ✅ API Key Repository (50+ tests)
  - Key generation and hashing
  - CRUD operations
  - Scope management (add, remove, set)
  - Validation and expiration
  - Request counting
  
- ✅ Scope Repository (8+ tests)
  - Scope lookup by name
  - Bulk existence checking
  - Scope creation
  
- ✅ Authentication Middleware (10+ tests)
  - Header extraction
  - Key validation
  - Permission checking (exact match, wildcards)
  - Authorization logic

### Integration Tests (`@pytest.mark.integration`)

End-to-end tests that validate API endpoints with a test database.

**Coverage:**
- ✅ API Key Endpoints (15+ tests)
  - Create API key with scopes
  - List with pagination
  - Get by ID
  - Update metadata and scopes
  - Revoke and delete
  - Permission enforcement
  
- ✅ Project Endpoints (8+ tests)
  - Create, list, get, update, delete
  - Permission enforcement
  
- ✅ Health Check Endpoints (2+ tests)
  - Basic health check
  - Readiness probe

## Test Fixtures

### Database Fixtures
- `test_engine`: In-memory SQLite database engine
- `test_session`: Async database session
- `override_get_session`: FastAPI dependency override

### Data Fixtures
- `test_project`: Sample project for testing
- `test_scopes`: Common scopes (read, write, admin)

### API Key Fixtures
- `admin_api_key`: Full access admin key
- `read_only_api_key`: Read-only access key

## Test Database

Tests use an **in-memory SQLite database** that is:
- ✅ Created fresh for each test function
- ✅ Completely isolated (no test interference)
- ✅ Automatically cleaned up after each test
- ✅ Fast (no disk I/O)

## Writing New Tests

### Unit Test Template

```python
import pytest
from src.database.repositories.api_key_repository import APIKeyRepository


@pytest.mark.unit
class TestMyFeature:
    """Test suite for my feature"""

    async def test_something(self, test_session, test_project):
        """Test description"""
        # Arrange
        repository = APIKeyRepository()
        
        # Act
        result = await repository.some_method(test_session, test_project.id)
        
        # Assert
        assert result is not None
        assert result.field == "expected_value"
```

### Integration Test Template

```python
import pytest
from httpx import AsyncClient
from main import app


@pytest.mark.integration
class TestMyEndpoint:
    """Integration tests for my endpoint"""

    async def test_endpoint_success(
        self,
        override_get_session,
        admin_api_key
    ):
        """Test successful request"""
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get(
                "/my/endpoint",
                headers={"X-API-Key": admin_api_key}
            )
        
        assert response.status_code == 200
        data = response.json()
        assert "expected_field" in data
```

## Coverage Goals

- **Overall Coverage**: 80%+ (currently achieving this)
- **Critical Paths**: 100% (authentication, key validation, CRUD operations)
- **Repository Layer**: 90%+ (comprehensive unit tests)
- **API Endpoints**: 85%+ (integration tests)

## Current Coverage

Run `pytest --cov=src --cov-report=term-missing` to see detailed coverage:

```
src/api/auth_middleware.py      95%
src/api/routes/keys.py           88%
src/database/repositories/       92%
src/database/models.py           85%
```

## CI/CD Integration

Tests are automatically run in GitHub Actions on:
- Every pull request
- Every push to main branch
- Nightly builds

Coverage reports are uploaded to Codecov.

## Debugging Tests

### Run with Print Statements
```bash
pytest -s
```

### Stop on First Failure
```bash
pytest -x
```

### Run Last Failed Tests
```bash
pytest --lf
```

### Run with Debugger
```bash
pytest --pdb
```

### Verbose Output
```bash
pytest -vv
```

## Performance

- **Unit Tests**: ~2-5 seconds total
- **Integration Tests**: ~10-15 seconds total
- **Full Suite**: ~20 seconds total

## Best Practices

1. ✅ **Isolate Tests**: Each test should be independent
2. ✅ **Use Fixtures**: Reuse common setup logic
3. ✅ **Clear Names**: Test names describe what they test
4. ✅ **AAA Pattern**: Arrange, Act, Assert
5. ✅ **Mock External Deps**: Don't test external services
6. ✅ **Test Edge Cases**: Invalid input, missing data, etc.
7. ✅ **Fast Feedback**: Unit tests should be very fast

## Troubleshooting

### SQLAlchemy MissingGreenlet Error
- Ensure `asyncio_mode = auto` in pytest.ini
- Use `async def` for all test functions
- Use `await` with async operations

### Import Errors
- Ensure virtual environment is activated
- Run `pip install -r requirements.txt`
- Check PYTHONPATH includes project root

### Database Errors
- Check that models are imported in conftest.py
- Verify `Base.metadata.create_all()` is called
- Ensure proper cleanup with `drop_all()`

## Future Enhancements

- [ ] Add load testing with Locust
- [ ] Add mutation testing with mutmut
- [ ] Add security testing with Bandit
- [ ] Add API contract testing
- [ ] Add performance benchmarks
