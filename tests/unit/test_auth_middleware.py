"""
Unit tests for authentication middleware.
"""

import pytest
from fastapi import HTTPException, status

from src.api.auth_middleware import get_api_key_from_header


@pytest.mark.unit
class TestAuthMiddleware:
    """Test suite for authentication middleware"""

    async def test_get_api_key_from_header_success(self):
        """Test extracting API key from header"""
        key = await get_api_key_from_header(x_api_key="test_key_123")
        assert key == "test_key_123"

    async def test_get_api_key_from_header_missing(self):
        """Test missing API key raises 401"""
        with pytest.raises(HTTPException) as exc_info:
            await get_api_key_from_header(x_api_key=None)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Missing API key" in exc_info.value.detail
