"""
Authentication and authorization middleware with scope-based permissions.
"""

from typing import List, Optional, Set
from fastapi import Header, HTTPException, status, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, time as datetime_time

from src.database.connection import get_session
from src.database.repositories.api_key_repository import api_key_repository
from src.database.models import AKMAPIKey
from src.logging_config import get_logger

logger = get_logger(__name__)


async def get_api_key_from_header(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key")
) -> str:
    """Extract API key from header"""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header in your request.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
    return x_api_key


async def get_current_api_key(
    request: Request,
    api_key: str = Depends(get_api_key_from_header),
    session: AsyncSession = Depends(get_session),
) -> AKMAPIKey:
    """
    Validate API key and return the full record with scopes and config.
    
    This is the base authentication dependency. All protected endpoints
    should use this or a permission checker that depends on it.
    """
    correlation_id = getattr(request.state, "correlation_id", "unknown")

    # Validate the key
    api_key_record = await api_key_repository.validate_key(session, api_key)

    if not api_key_record:
        # Log como ERROR para visibilidade explícita em casos de autenticação inválida
        logger.error(
            "Invalid API key attempt",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path,
                "key_prefix": api_key[:12] if api_key else "none",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Store in request state for use by other middleware/dependencies
    request.state.api_key = api_key_record
    request.state.api_key_id = api_key_record.id
    request.state.api_key_name = api_key_record.name
    
    if api_key_record.config:
        request.state.api_key_config = api_key_record.config

    logger.info(
        f"API key authenticated: {api_key_record.name}",
        extra={
            "correlation_id": correlation_id,
            "api_key_name": api_key_record.name,
            "api_key_id": api_key_record.id,
            "project_id": api_key_record.project_id,
            "request_count": api_key_record.request_count,
        },
    )

    return api_key_record


class PermissionChecker:
    """
    Dependency class for checking if API key has required permissions (scopes).
    
    Usage:
        @router.get("/projects")
        async def list_projects(
            api_key: AKMAPIKey = Depends(PermissionChecker(["akm:projects:read"]))
        ):
            ...
    """
    
    def __init__(self, required_scopes: List[str]):
        """
        Initialize with required scopes.
        
        Args:
            required_scopes: List of scope names required for this endpoint
        """
        self.required_scopes = required_scopes
    
    async def __call__(
        self,
        request: Request,
        api_key: AKMAPIKey = Depends(get_current_api_key),
        session: AsyncSession = Depends(get_session)
    ) -> AKMAPIKey:
        """
        Verify that the API key has all required scopes and passes config checks.
        
        Returns:
            The validated API key record
            
        Raises:
            HTTPException: If permissions are insufficient or config restrictions fail
        """
        correlation_id = getattr(request.state, "correlation_id", "unknown")
        
        # Check configuration restrictions
        await self._check_config_restrictions(request, api_key, session)
        
        # Extract scope names from relationships
        # AKMAPIKeyScope has a relationship 'scope' that points to AKMScope
        key_scopes = {scope.scope.scope_name for scope in api_key.scopes}
        
        # Super admin has access to everything
        if "akm:admin:*" in key_scopes or "akm:*" in key_scopes:
            logger.info(
                "Super admin access granted",
                extra={
                    "correlation_id": correlation_id,
                    "api_key_id": api_key.id,
                    "endpoint": request.url.path
                }
            )
            return api_key
        
        # Check each required scope
        missing_scopes = []
        for required in self.required_scopes:
            if not self._has_permission(required, key_scopes):
                missing_scopes.append(required)
        
        if missing_scopes:
            logger.warning(
                "Insufficient permissions",
                extra={
                    "correlation_id": correlation_id,
                    "api_key_id": api_key.id,
                    "missing_scopes": missing_scopes,
                    "has_scopes": list(key_scopes),
                    "endpoint": request.url.path
                }
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Missing scopes: {', '.join(missing_scopes)}"
            )
        
        logger.debug(
            "Permission check passed",
            extra={
                "correlation_id": correlation_id,
                "api_key_id": api_key.id,
                "required_scopes": self.required_scopes,
                "endpoint": request.url.path
            }
        )
        
        return api_key
    
    def _has_permission(self, required: str, available: Set[str]) -> bool:
        """
        Check if the required scope is available.
        
        Supports wildcards: akm:projects:* includes read/write/delete
        
        Args:
            required: Required scope name
            available: Set of available scope names
            
        Returns:
            True if permission is granted
        """
        # Exact match
        if required in available:
            return True
        
        # Check wildcard permissions
        parts = required.split(':')
        for i in range(len(parts)):
            wildcard = ':'.join(parts[:i+1]) + ':*'
            if wildcard in available:
                return True
        
        return False
    
    async def _check_config_restrictions(
        self,
        request: Request,
        api_key: AKMAPIKey,
        session: AsyncSession
    ):
        """
        Check configuration restrictions (IP whitelist, time restrictions).
        
        Rate limiting is handled separately by rate limit middleware.
        """
        config = api_key.config
        
        if not config:
            return
        
        # Check IP whitelist
        if config.ip_whitelist_enabled and config.allowed_ips:
            client_ip = self._get_client_ip(request)
            
            if not self._is_ip_allowed(client_ip, config.allowed_ips):
                logger.warning(
                    "IP address not whitelisted",
                    extra={
                        "api_key_id": api_key.id,
                        "client_ip": client_ip,
                        "allowed_ips": config.allowed_ips
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. IP address {client_ip} is not whitelisted."
                )
        
        # Check time restrictions
        if config.allowed_time_start and config.allowed_time_end:
            current_time = datetime.utcnow().time()
            
            if not self._is_time_allowed(current_time, config.allowed_time_start, config.allowed_time_end):
                logger.warning(
                    "Access outside allowed time window",
                    extra={
                        "api_key_id": api_key.id,
                        "current_time": current_time.isoformat(),
                        "allowed_start": config.allowed_time_start.isoformat(),
                        "allowed_end": config.allowed_time_end.isoformat()
                    }
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Allowed time window: {config.allowed_time_start} - {config.allowed_time_end}"
                )
    
    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request"""
        # Check for forwarded IP (behind proxy)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check for real IP
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fallback to direct client
        return request.client.host if request.client else "unknown"
    
    def _is_ip_allowed(self, client_ip: str, allowed_ips: List[str]) -> bool:
        """
        Check if client IP is in allowed list.
        
        Supports individual IPs and CIDR notation.
        """
        import ipaddress
        
        try:
            client_addr = ipaddress.ip_address(client_ip)
            
            for allowed in allowed_ips:
                try:
                    # Try as network (CIDR)
                    if '/' in allowed:
                        network = ipaddress.ip_network(allowed, strict=False)
                        if client_addr in network:
                            return True
                    # Try as individual IP
                    else:
                        if client_addr == ipaddress.ip_address(allowed):
                            return True
                except ValueError:
                    continue
            
            return False
            
        except ValueError:
            logger.error(f"Invalid IP address: {client_ip}")
            return False
    
    def _is_time_allowed(
        self,
        current: datetime_time,
        start: datetime_time,
        end: datetime_time
    ) -> bool:
        """Check if current time is within allowed window"""
        if start <= end:
            # Normal case: 08:00 - 18:00
            return start <= current <= end
        else:
            # Wraps midnight: 22:00 - 06:00
            return current >= start or current <= end


async def optional_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> Optional[AKMAPIKey]:
    """
    Optional API key verification (doesn't raise exception if missing).
    
    Useful for endpoints that have both public and authenticated access.
    """
    if not x_api_key:
        return None
    
    try:
        api_key_record = await api_key_repository.validate_key(session, x_api_key)
        if api_key_record:
            request.state.api_key = api_key_record
            request.state.api_key_id = api_key_record.id
        return api_key_record
    except Exception as e:
        logger.warning(f"Optional API key validation failed: {e}")
        return None
