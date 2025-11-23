"""
Audit Middleware for automatic operation tracking.

Automatically logs all API operations to audit trail with minimal overhead.
"""

import time
import json
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.audit_logger import AuditLogger
from src.database.connection import get_async_session
from src.logging_config import get_logger

logger = get_logger(__name__)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware that automatically audits all API requests.
    
    Features:
    - Automatic correlation ID generation
    - Request/response capture with sanitization
    - Performance tracking
    - Error logging
    - Selective auditing (exclude health checks, static files)
    """
    
    # Paths to exclude from audit logging
    EXCLUDED_PATHS = {
        "/health",
        "/healthz", 
        "/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/favicon.ico"
    }
    
    # Methods to exclude
    EXCLUDED_METHODS = {"OPTIONS", "HEAD"}
    
    # Max request/response body size to log (bytes)
    MAX_BODY_SIZE = 10_000  # 10KB
    
    def __init__(self, app: ASGIApp):
        """Initialize audit middleware."""
        super().__init__(app)
    
    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request and log to audit trail.
        """
        # Skip excluded paths and methods
        if (
            request.url.path in self.EXCLUDED_PATHS 
            or request.method in self.EXCLUDED_METHODS
            or request.url.path.startswith("/static/")
        ):
            return await call_next(request)
        
        # Generate correlation ID for this request
        correlation_id = AuditLogger.generate_correlation_id()
        
        # Store correlation ID in request state for access in routes
        request.state.correlation_id = correlation_id
        
        # Start timing
        start_time = time.time()
        
        # Capture request body (if present and not too large)
        request_payload = None
        if request.method in {"POST", "PUT", "PATCH"}:
            try:
                body = await request.body()
                if len(body) <= self.MAX_BODY_SIZE:
                    # Try to parse as JSON
                    try:
                        request_payload = json.loads(body.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        request_payload = {"_raw": "non-json body"}
                else:
                    request_payload = {"_size": len(body), "_note": "body too large to log"}
                
                # Important: Re-populate body for route handlers
                async def receive():
                    return {"type": "http.request", "body": body}
                
                request._receive = receive
            
            except Exception as e:
                logger.warning(f"Failed to capture request body: {e}")
        
        # Process request and capture response
        response = None
        error_message = None
        status = "success"
        
        try:
            response = await call_next(request)
            
            # Determine status based on HTTP status code
            if response.status_code >= 400:
                status = "failure" if response.status_code >= 500 else "denied"
            
        except Exception as e:
            # Request processing failed
            error_message = str(e)
            status = "failure"
            
            logger.error(
                f"Request processing failed: {e}",
                extra={
                    "correlation_id": correlation_id,
                    "path": request.url.path,
                    "method": request.method
                },
                exc_info=True
            )
            
            # Return error response
            response = JSONResponse(
                status_code=500,
                content={"detail": "Internal server error", "correlation_id": correlation_id}
            )
        
        # Calculate duration
        duration_ms = (time.time() - start_time) * 1000
        
        # Extract authentication context (if available)
        api_key_id = getattr(request.state, "api_key_id", None)
        project_id = getattr(request.state, "project_id", None)
        
        # Determine operation and resource type from path
        operation, resource_type = self._infer_operation_details(
            request.url.path, 
            request.method
        )
        
        # Audit log the operation (async in background)
        try:
            # Get database session
            async with get_async_session() as db:
                audit_logger = AuditLogger(db)
                audit_logger.correlation_id = correlation_id
                
                await audit_logger.log_operation(
                    operation=operation,
                    resource_type=resource_type,
                    action=request.method,
                    request=request,
                    api_key_id=api_key_id,
                    project_id=project_id,
                    request_payload=request_payload,
                    response_status=response.status_code,
                    error_message=error_message,
                    status=status,
                    correlation_id=correlation_id,
                    metadata={
                        "duration_ms": round(duration_ms, 2),
                        "user_agent": request.headers.get("User-Agent"),
                        "content_type": request.headers.get("Content-Type")
                    }
                )
                
                await db.commit()
        
        except Exception as e:
            # Don't fail request if audit logging fails
            logger.error(
                f"Audit logging failed: {e}",
                extra={"correlation_id": correlation_id},
                exc_info=True
            )
        
        # Add correlation ID to response headers
        response.headers["X-Correlation-ID"] = correlation_id
        
        return response
    
    @staticmethod
    def _infer_operation_details(path: str, method: str) -> tuple[str, str]:
        """
        Infer operation name and resource type from path and method.
        
        Examples:
            POST /akm/projects -> ("create_project", "project")
            GET /akm/keys/123 -> ("get_api_key", "api_key")
            DELETE /akm/scopes/5 -> ("delete_scope", "scope")
        
        Returns:
            Tuple of (operation_name, resource_type)
        """
        # Remove /akm prefix if present
        path = path.replace("/akm/", "/").strip("/")
        
        # Split path into segments
        segments = [s for s in path.split("/") if s]
        
        if not segments:
            return ("unknown", "unknown")
        
        # Get resource from first segment
        resource = segments[0].rstrip("s")  # Remove trailing 's' for plural
        
        # Map common resource names
        resource_map = {
            "project": "project",
            "key": "api_key",
            "scope": "scope",
            "webhook": "webhook",
            "alert": "alert",
            "config": "config",
            "audit": "audit_log"
        }
        
        resource_type = resource_map.get(resource, resource)
        
        # Map HTTP methods to operations
        method_map = {
            "GET": "read" if len(segments) > 1 else "list",
            "POST": "create",
            "PUT": "update",
            "PATCH": "update",
            "DELETE": "delete"
        }
        
        action = method_map.get(method, "execute")
        
        # Build operation name
        operation = f"{action}_{resource_type}"
        
        return (operation, resource_type)
