# Testing Guide

This guide covers testing practices and procedures for the API Key Management Service.

## Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Test Structure](#test-structure)
- [Writing Tests](#writing-tests)
- [Running Tests](#running-tests)
- [Continuous Integration](#continuous-integration)
- [Code Coverage](#code-coverage)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

The project uses `pytest` for testing with the following characteristics:

- **Unit Tests**: Fast, isolated tests for individual components
- **Integration Tests**: End-to-end API endpoint tests
- **Async Support**: Full async/await testing with `pytest-asyncio`
- **Test Database**: In-memory SQLite for fast test execution
- **Coverage**: Code coverage tracking with `pytest-cov`
- **CI/CD**: Automated testing via GitHub Actions

## Quick Start

### Install Dependencies

```bash
# Install all dependencies including test tools
pip install -r requirements.txt
```

### Run Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test types
pytest -m unit         # Only unit tests
pytest -m integration  # Only integration tests
```

## Test Structure

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── __init__.py
├── unit/                       # Unit tests (fast, isolated)
│   ├── __init__.py
│   ├── test_auth.py           # Authentication logic tests
│   └── test_models.py         # Database model tests
└── integration/                # Integration tests (API endpoints)
    ├── __init__.py
    └── test_api_endpoints.py  # End-to-end API tests
```

### Test Categories

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests (fast, isolated)
- `@pytest.mark.integration` - Integration tests (slower, database)
- `@pytest.mark.auth` - Authentication-related tests
- `@pytest.mark.slow` - Slow-running tests

## Writing Tests

### Basic Test Structure

```python
import pytest

@pytest.mark.unit
def test_simple_function():
    """Test description."""
    result = simple_function()
    assert result == expected_value
```

### Async Tests

```python
import pytest

@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_function(test_session):
    """Test async function."""
    result = await async_function(test_session)
    assert result is not None
```

### Using Fixtures

Fixtures provide reusable test setup:

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_with_api_key(test_api_key):
    """Test using API key fixture."""
    api_key_string, api_key_record = test_api_key
    
    assert api_key_string is not None
    assert api_key_record.is_active is True
```

### Integration Tests

```python
import pytest
from fastapi.testclient import TestClient

@pytest.mark.integration
def test_api_endpoint(client: TestClient):
    """Test API endpoint."""
    response = client.get("/api/health")
    
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
```

### Testing Authentication

```python
@pytest.mark.integration
@pytest.mark.auth
async def test_authenticated_endpoint(client, test_api_key):
    """Test endpoint with authentication."""
    api_key, _ = test_api_key
    headers = {"X-API-Key": api_key}
    
    response = client.get("/api/cds", headers=headers)
    
    assert response.status_code == 200
```

## Available Fixtures

### Database Fixtures

- `test_engine` - Test database engine
- `test_session` - Async database session
- `api_key_repository` - API key repository instance

### API Fixtures

- `client` - Synchronous FastAPI test client
- `async_client` - Asynchronous HTTP client
- `test_api_key` - Pre-created test API key

### Data Fixtures

- `sample_cds_data` - Sample CDS data for testing
- `invalid_api_key` - Invalid API key string

### Environment Fixtures

- `mock_env_vars` - Mock environment variables

## Running Tests

### Basic Commands

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/unit/test_auth.py

# Run specific test
pytest tests/unit/test_auth.py::TestAPIKeyRepository::test_create_api_key
```

### Filtering Tests

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only auth tests
pytest -m auth

# Run all except slow tests
pytest -m "not slow"

# Combine markers
pytest -m "unit and auth"
```

### Coverage Reports

```bash
# Run with coverage
pytest --cov=src

# Generate HTML coverage report
pytest --cov=src --cov-report=html

# Generate XML report (for CI)
pytest --cov=src --cov-report=xml

# Show missing lines
pytest --cov=src --cov-report=term-missing
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest -n auto  # Auto-detect CPU cores
pytest -n 4     # Use 4 workers
```

### Debugging Tests

```bash
# Stop on first failure
pytest -x

# Show local variables on failure
pytest -l

# Enter debugger on failure
pytest --pdb

# Show print statements
pytest -s
```

## Continuous Integration

Tests run automatically on GitHub Actions for:

- **Push events** to `main`, `master`, `develop` branches
- **Pull requests** to these branches
- **Multiple Python versions**: 3.11, 3.12

### CI Pipeline Steps

1. **Linting** - Code style checks (flake8, black)
2. **Unit Tests** - Fast isolated tests
3. **Integration Tests** - API endpoint tests
4. **Coverage** - Upload to Codecov
5. **Quality Checks** - Security scans, type checking
6. **Build Check** - Verify application startup

### Viewing CI Results

- Check the **Actions** tab in GitHub
- View badges on README for quick status
- Download artifacts for detailed coverage reports

## Code Coverage

### Coverage Goals

- **Overall**: Aim for 80%+ coverage
- **Critical paths**: 90%+ (auth, data handling)
- **Utilities**: 70%+ acceptable

### Viewing Coverage

```bash
# Generate HTML report
pytest --cov=src --cov-report=html

# Open report in browser
# Windows
start htmlcov/index.html

# macOS
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html
```

### Coverage Configuration

Coverage settings in `pytest.ini`:

```ini
[coverage:run]
source = src
omit = 
    */tests/*
    */migrations/*
```

## Best Practices

### Test Naming

```python
# Good
def test_create_api_key_success():
def test_validate_api_key_when_revoked():
def test_cds_endpoint_requires_authentication():

# Bad
def test1():
def test_stuff():
def my_test():
```

### Test Organization

- **One assertion per test** (when possible)
- **Arrange-Act-Assert** pattern
- **Clear test descriptions**
- **Independent tests** (no dependencies)

### Example Test

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_api_key_increments_counter(api_key_repository):
    """Test that request counter increments on validation."""
    # Arrange
    api_key, record = await api_key_repository.create_key("Test", "Desc")
    initial_count = record.request_count
    
    # Act
    await api_key_repository.validate_key(api_key)
    updated = await api_key_repository.get_by_id(record.id)
    
    # Assert
    assert updated.request_count == initial_count + 1
```

### Fixture Best Practices

```python
# Use function scope for most fixtures
@pytest.fixture(scope="function")
async def test_data():
    data = create_test_data()
    yield data
    await cleanup_test_data(data)

# Use session scope for expensive setup
@pytest.fixture(scope="session")
def app_config():
    return load_config()
```

### Mocking

```python
from unittest.mock import patch, MagicMock

@pytest.mark.unit
def test_with_mock():
    """Test using mock."""
    with patch('module.function') as mock_func:
        mock_func.return_value = "mocked"
        result = call_function_that_uses_function()
        assert result == "mocked"
        mock_func.assert_called_once()
```

## Troubleshooting

### Common Issues

#### 1. Import Errors

```bash
# Problem: ModuleNotFoundError
# Solution: Install test dependencies
pip install -r requirements.txt

# Ensure pytest is installed
pip install pytest pytest-asyncio
```

#### 2. Async Test Failures

```python
# Problem: RuntimeError: Event loop is closed
# Solution: Use pytest-asyncio and mark tests

import pytest

@pytest.mark.asyncio  # Required for async tests
async def test_async_function():
    result = await my_async_function()
    assert result
```

#### 3. Database Connection Issues

```python
# Problem: Database connection errors
# Solution: Use test fixtures that provide in-memory database

@pytest.mark.asyncio
async def test_with_db(test_session):  # Use test_session fixture
    result = await query_database(test_session)
    assert result
```

#### 4. Fixture Not Found

```bash
# Problem: fixture 'xyz' not found
# Solution: Check conftest.py and import statements

# Ensure fixture is defined in conftest.py
# Or import it from the correct module
```

### Debugging Tips

```bash
# Run single test with full output
pytest tests/unit/test_auth.py::test_create_api_key -v -s

# Show fixture setup
pytest --setup-show

# List all fixtures
pytest --fixtures

# Run with debugging
pytest --pdb --pdbcls=IPython.terminal.debugger:TerminalPdb
```

### Performance Issues

```bash
# Profile slow tests
pytest --durations=10  # Show 10 slowest tests

# Run in parallel
pytest -n auto

# Skip slow tests during development
pytest -m "not slow"
```

## Additional Resources

### Documentation

- [Pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)

### Project Documentation

- [README.md](../README.md) - Project overview
- [AUTHENTICATION.md](AUTHENTICATION.md) - Authentication system
- [API_KEY_MANAGEMENT.md](API_KEY_MANAGEMENT.md) - API key management

---

## Contributing

When contributing tests:

1. Write tests for new features
2. Maintain test coverage above 80%
3. Follow existing test patterns
4. Add docstrings to test functions
5. Run full test suite before PR
6. Check CI passes on GitHub

---

**Happy Testing!** 🧪✨
