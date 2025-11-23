"""
API Versioning utilities and configuration.
"""

from enum import Enum
from typing import Optional
from fastapi import Header, HTTPException, status


class APIVersion(str, Enum):
    """Supported API versions."""
    V1 = "v1"
    # V2 = "v2"  # Futuro


# Default version used when no version is specified
DEFAULT_VERSION = APIVersion.V1

# Latest stable version
LATEST_VERSION = APIVersion.V1

# Deprecated versions (will show warning but still work)
DEPRECATED_VERSIONS: set[APIVersion] = set()

# Sunset versions (no longer supported)
SUNSET_VERSIONS: set[APIVersion] = set()


def get_api_version_from_header(
    x_api_version: Optional[str] = Header(None, alias="X-API-Version")
) -> APIVersion:
    """
    Get API version from request header.
    
    Allows clients to specify version via header instead of URL path:
    X-API-Version: v1
    
    Args:
        x_api_version: API version from header
        
    Returns:
        APIVersion enum value
        
    Raises:
        HTTPException: If version is invalid or sunset
    """
    if not x_api_version:
        return DEFAULT_VERSION
    
    try:
        version = APIVersion(x_api_version.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid API version: {x_api_version}. Supported versions: {[v.value for v in APIVersion]}"
        )
    
    if version in SUNSET_VERSIONS:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail=f"API version {version.value} has been sunset and is no longer available."
        )
    
    return version


def get_deprecation_warning(version: APIVersion) -> Optional[str]:
    """
    Get deprecation warning message for a version if applicable.
    
    Args:
        version: API version to check
        
    Returns:
        Warning message if deprecated, None otherwise
    """
    if version in DEPRECATED_VERSIONS:
        return (
            f"API version {version.value} is deprecated and will be sunset soon. "
            f"Please migrate to {LATEST_VERSION.value}."
        )
    return None


def validate_version_compatibility(
    required_version: APIVersion,
    current_version: APIVersion
) -> bool:
    """
    Check if current version is compatible with required version.
    
    Args:
        required_version: Minimum required version
        current_version: Current API version being used
        
    Returns:
        True if compatible, False otherwise
    """
    # Extract version numbers (v1 -> 1, v2 -> 2)
    required_num = int(required_version.value[1:])
    current_num = int(current_version.value[1:])
    
    # Current version must be >= required version
    return current_num >= required_num
