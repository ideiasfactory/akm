"""
Dynamic CORS middleware for per-project CORS configuration.

This middleware allows different projects to have different CORS origins
based on their configuration in the database.
"""

from typing import List, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.types import ASGIApp

from src.database.connection import get_engine
from src.database.repositories.project_configuration_repository import project_configuration_repository
from src.database.repositories.api_key_repository import api_key_repository
from src.config import settings
from src.logging_config import get_logger
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = get_logger(__name__)


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    """
    Dynamic CORS middleware that loads allowed origins per project.
    
    Priority:
    1. Project-level configuration (from database)
    2. Global defaults (from settings)
    """
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.global_origins = settings.cors_origins_list
        
    async def dispatch(self, request: Request, call_next):
        """
        Process request and apply dynamic CORS headers.
        """
        # Get API key from header
        api_key_value = request.headers.get("X-API-Key")
        
        # Determine allowed origins
        allowed_origins = await self._get_allowed_origins(api_key_value)
        
        # Get request origin
        origin = request.headers.get("origin")
        
        # Handle preflight OPTIONS request
        if request.method == "OPTIONS":
            return self._handle_preflight(origin, allowed_origins)
        
        # Process request
        response = await call_next(request)
        
        # Add CORS headers to response
        if origin and self._is_origin_allowed(origin, allowed_origins):
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Expose-Headers"] = "X-Correlation-ID, X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset, Retry-After"
        
        return response
    
    async def _get_allowed_origins(self, api_key_value: Optional[str]) -> List[str]:
        """
        Get allowed CORS origins for the API key's project.
        
        Returns:
            List of allowed origin URLs
        """
        if not api_key_value:
            # No API key, use global defaults
            return self.global_origins
        
        try:
            # Get synchronous engine for this middleware
            engine = get_engine()
            
            with Session(engine) as session:
                # Get API key
                api_key = api_key_repository.get_key_by_value_sync(session, api_key_value)
                
                if not api_key:
                    # Invalid key, use global defaults
                    return self.global_origins
                
                # Get project configuration
                config = project_configuration_repository.get_by_project_id_sync(
                    session, 
                    api_key.project_id
                )
                
                if config and config.cors_origins:
                    # Project has custom CORS configuration
                    logger.debug(
                        f"Using project-specific CORS origins for project {api_key.project_id}",
                        extra={"project_id": api_key.project_id, "origin_count": len(config.cors_origins)}
                    )
                    return config.cors_origins
                
                # No custom config, use global defaults
                return self.global_origins
                
        except Exception as e:
            logger.error(
                f"Error loading CORS configuration: {e}",
                extra={"error": str(e)}
            )
            # On error, use global defaults
            return self.global_origins
    
    def _is_origin_allowed(self, origin: str, allowed_origins: List[str]) -> bool:
        """
        Check if origin is in allowed list.
        
        Args:
            origin: Request origin
            allowed_origins: List of allowed origins
            
        Returns:
            True if origin is allowed
        """
        return origin in allowed_origins
    
    def _handle_preflight(self, origin: Optional[str], allowed_origins: List[str]) -> Response:
        """
        Handle CORS preflight OPTIONS request.
        
        Args:
            origin: Request origin
            allowed_origins: List of allowed origins
            
        Returns:
            Response with CORS headers
        """
        headers = {}
        
        if origin and self._is_origin_allowed(origin, allowed_origins):
            headers["Access-Control-Allow-Origin"] = origin
            headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
            headers["Access-Control-Allow-Headers"] = "X-API-Key, Content-Type, Authorization, X-Correlation-ID"
            headers["Access-Control-Allow-Credentials"] = "true"
            headers["Access-Control-Max-Age"] = "600"  # Cache preflight for 10 minutes
        
        return Response(status_code=200, headers=headers)
