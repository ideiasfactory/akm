"""
API Versioning Middleware
Adds deprecation warnings and version information to responses.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable
import re

from src.api.versioning import (
    APIVersion,
    get_deprecation_warning,
    LATEST_VERSION,
    DEPRECATED_VERSIONS,
    SUNSET_VERSIONS,
)
from src.logging_config import get_logger, log_with_context

logger = get_logger(__name__)


class VersioningMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle API versioning and add deprecation warnings.
    
    Features:
    - Detects API version from URL path
    - Adds deprecation headers if version is deprecated
    - Adds current/latest version headers
    - Logs usage of deprecated versions
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and add version headers to response."""
        
        # Extract version from URL path
        version = self._extract_version_from_path(request.url.path)
        
        # Get correlation_id if available
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        
        # Check if using legacy (unversioned) endpoint
        is_legacy = self._is_legacy_endpoint(request.url.path)
        
        # Log deprecated/legacy usage
        if is_legacy:
            log_with_context(
                logger,
                'warning',
                f"Legacy (unversioned) endpoint accessed: {request.url.path}",
                correlation_id=correlation_id,
                path=request.url.path,
                method=request.method,
                client=request.client.host if request.client else None,
                recommended_path=self._get_versioned_path(request.url.path)
            )
        elif version and version in DEPRECATED_VERSIONS:
            log_with_context(
                logger,
                'warning',
                f"Deprecated API version accessed: {version.value}",
                correlation_id=correlation_id,
                path=request.url.path,
                version=version.value,
                latest_version=LATEST_VERSION.value
            )
        
        # Process request
        response = await call_next(request)
        
        # Add version headers
        if version:
            response.headers["X-API-Version"] = version.value
        elif is_legacy:
            response.headers["X-API-Version"] = "legacy"
        
        # Add latest version header
        response.headers["X-API-Latest-Version"] = LATEST_VERSION.value
        
        # Add deprecation headers if applicable
        if is_legacy:
            response.headers["X-API-Deprecated"] = "true"
            response.headers["X-API-Deprecated-Message"] = (
                f"Unversioned endpoints are deprecated. Use /akm/{LATEST_VERSION.value} instead."
            )
            response.headers["X-API-Sunset-Date"] = "2026-01-01"  # Example sunset date
        elif version and version in DEPRECATED_VERSIONS:
            warning_msg = get_deprecation_warning(version)
            if warning_msg:
                response.headers["X-API-Deprecated"] = "true"
                response.headers["X-API-Deprecated-Message"] = warning_msg
                response.headers["X-API-Sunset-Date"] = "2026-06-01"  # Example sunset date
        
        return response
    
    def _extract_version_from_path(self, path: str) -> APIVersion | None:
        """
        Extract API version from URL path.
        
        Examples:
        - /akm/v1/keys -> v1
        - /akm/v2/projects -> v2
        - /akm/keys -> None (legacy)
        
        Args:
            path: URL path
            
        Returns:
            APIVersion if found, None otherwise
        """
        # Pattern: /akm/v{number}/...
        pattern = r'/akm/(v\d+)/'
        match = re.search(pattern, path)
        
        if match:
            version_str = match.group(1)
            try:
                return APIVersion(version_str)
            except ValueError:
                return None
        
        return None
    
    def _is_legacy_endpoint(self, path: str) -> bool:
        """
        Check if path is a legacy (unversioned) endpoint.
        
        Legacy endpoints:
        - /akm/keys (no version)
        - /akm/projects (no version)
        
        NOT legacy:
        - /akm/v1/keys (versioned)
        - /health (not under /akm)
        - / (home)
        
        Args:
            path: URL path
            
        Returns:
            True if legacy endpoint, False otherwise
        """
        # Check if path starts with /akm/ but doesn't have version
        if path.startswith('/akm/'):
            # Exclude versioned paths
            if not re.search(r'/akm/v\d+/', path):
                # Exclude non-API paths under /akm
                api_paths = [
                    '/keys', '/projects', '/scopes', '/webhooks',
                    '/configs', '/alerts', '/openapi-scopes', '/audit', '/sensitive-fields'
                ]
                return any(api_path in path for api_path in api_paths)
        
        return False
    
    def _get_versioned_path(self, legacy_path: str) -> str:
        """
        Convert legacy path to versioned path.
        
        Example:
        - /akm/keys -> /akm/v1/keys
        - /akm/projects/1 -> /akm/v1/projects/1
        
        Args:
            legacy_path: Legacy (unversioned) path
            
        Returns:
            Versioned path
        """
        return legacy_path.replace('/akm/', f'/akm/{LATEST_VERSION.value}/', 1)
