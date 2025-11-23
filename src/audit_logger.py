"""
Enhanced Audit Logging System with Integrity Protection.

This module provides a comprehensive audit logging system with:
- Correlation IDs for tracking related operations
- SHA-256 hash for integrity verification
- Microsecond precision timestamps
- Structured logging to console and database
- Automatic sanitization of sensitive data
"""

import uuid
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional, List
from contextlib import asynccontextmanager

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import AKMAuditLog
from src.sensitive_field_manager import SensitiveFieldManager
from src.config import settings
from src.logging_config import get_logger

# Console logger for audit events
audit_logger = get_logger("audit")


class AuditLogger:
    """Advanced audit logger with integrity protection and database persistence.

    Dynamic sensitive fields are loaded from:
    - JSON configuration file (`data/sensitive_fields.json`)
    - Database control table (`akm_sensitive_fields`)
    - Global settings (environment variables)
    Merge order (lowest precedence first): file < db < per-call overrides.
    """

    def __init__(self, db: AsyncSession, sensitive_field_manager: Optional[SensitiveFieldManager] = None):
        self.db = db
        self.correlation_id: Optional[str] = None
        self._sf_manager = sensitive_field_manager or SensitiveFieldManager(db)
        self._cached_fields: Dict[str, Dict[str, Any]] = {}
        self._global_strategy: Dict[str, Any] = {}

    async def _ensure_sensitive_fields_loaded(self) -> None:
        # Load merged fields + global strategy
        self._cached_fields = await self._sf_manager.get_fields()
        self._global_strategy = self._sf_manager.get_global_strategy()
    
    @staticmethod
    def generate_correlation_id() -> str:
        """Generate unique correlation ID for tracking related operations."""
        return str(uuid.uuid4())
    
    def _apply_sanitization(self, key: str, value: Any) -> Any:
        """Apply sanitization strategy for a sensitive field value."""
        field_cfg = self._cached_fields.get(key.lower(), {})
        strategy = field_cfg.get("strategy") or self._global_strategy.get("strategy", "redact")
        if strategy == "redact":
            replacement = field_cfg.get("replacement") or self._global_strategy.get("replacement", "[REDACTED]")
            return replacement
        if strategy == "mask" and isinstance(value, str):
            show_start = field_cfg.get("mask_show_start") or self._global_strategy.get("mask_show_start", 3)
            show_end = field_cfg.get("mask_show_end") or self._global_strategy.get("mask_show_end", 2)
            mask_char = field_cfg.get("mask_char") or self._global_strategy.get("mask_char", "*")
            if len(value) <= show_start + show_end:
                return mask_char * len(value)
            middle_len = len(value) - (show_start + show_end)
            return value[:show_start] + (mask_char * middle_len) + value[-show_end:]
        # Fallback
        return "[REDACTED]"

    def sanitize_data(self, data: Any, max_depth: int = 5) -> Any:
        """
        Recursively sanitize sensitive data from logs.
        
        Args:
            data: Data to sanitize (dict, list, or primitive)
            max_depth: Maximum recursion depth to prevent infinite loops
        
        Returns:
            Sanitized copy of data with sensitive fields redacted
        """
        if max_depth <= 0:
            return "[MAX_DEPTH_REACHED]"
        
        if isinstance(data, dict):
            sanitized: Dict[str, Any] = {}
            for key, value in data.items():
                key_lower = str(key).lower()
                is_sensitive = key_lower in self._cached_fields or any(part in key_lower for part in self._cached_fields.keys())
                if is_sensitive:
                    sanitized[key] = self._apply_sanitization(key_lower, value)
                else:
                    sanitized[key] = self.sanitize_data(value, max_depth - 1)
            return sanitized
        
        elif isinstance(data, list):
            return [self.sanitize_data(item, max_depth - 1) for item in data]
        
        elif isinstance(data, (str, int, float, bool, type(None))):
            return data
        
        else:
            # For other types, convert to string
            return str(data)
    
    @staticmethod
    def extract_client_ip(request: Request) -> Optional[str]:
        """
        Extract client IP address from request.
        
        Checks X-Forwarded-For, X-Real-IP headers for proxied requests.
        """
        # Check X-Forwarded-For (proxy/load balancer)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Get first IP (client)
            return forwarded_for.split(",")[0].strip()
        
        # Check X-Real-IP (nginx proxy)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct client
        if request.client:
            return request.client.host
        
        return None
    
    async def log_operation(
        self,
        operation: str,
        resource_type: str,
        action: str,
        request: Optional[Request] = None,
        resource_id: Optional[str] = None,
        api_key_id: Optional[int] = None,
        project_id: Optional[int] = None,
        request_payload: Optional[Dict[str, Any]] = None,
        response_status: Optional[int] = None,
        response_payload: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        status: str = "success",
        metadata: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ) -> AKMAuditLog:
        """
        Log an operation to both console and database with integrity protection.
        
        Args:
            operation: Operation name (e.g., "create_api_key", "delete_project")
            resource_type: Type of resource (e.g., "api_key", "project", "scope")
            action: HTTP method or action type (e.g., "POST", "DELETE")
            request: FastAPI request object
            resource_id: ID of affected resource
            api_key_id: ID of API key used for operation
            project_id: ID of project (for multi-tenancy filtering)
            request_payload: Request body (will be sanitized)
            response_status: HTTP response status code
            response_payload: Response body (will be sanitized)
            error_message: Error details if operation failed
            status: Operation status ("success", "failure", "denied")
            metadata: Additional context
            correlation_id: Optional correlation ID (generated if not provided)
        
        Returns:
            Created audit log entry
        """
        # Generate or use provided correlation ID
        if correlation_id is None:
            correlation_id = self.correlation_id or self.generate_correlation_id()
        
        # Extract request context
        endpoint = request.url.path if request else "unknown"
        http_method = request.method if request else action
        ip_address = self.extract_client_ip(request) if request else None
        user_agent = request.headers.get("User-Agent") if request else None
        
        # Sanitize payloads
        await self._ensure_sensitive_fields_loaded()
        sanitized_request = self.sanitize_data(request_payload) if request_payload else None
        sanitized_response = self.sanitize_data(response_payload) if response_payload else None
        
        # Create timestamp with microsecond precision
        timestamp = datetime.now(timezone.utc)
        
        # Create audit log entry
        audit_entry = AKMAuditLog(
            correlation_id=correlation_id,
            api_key_id=api_key_id,
            project_id=project_id,
            operation=operation,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            endpoint=endpoint,
            http_method=http_method,
            ip_address=ip_address,
            user_agent=user_agent,
            request_payload=sanitized_request,
            response_status=response_status,
            response_payload=sanitized_response,
            error_message=error_message,
            extra_metadata=metadata,
            timestamp=timestamp,
            status=status
        )
        
        # Calculate integrity hash
        audit_entry.entry_hash = audit_entry.calculate_hash()
        
        # Log to console (structured JSON)
        audit_logger.info(
            f"AUDIT: {operation}",
            extra={
                "audit_type": "operation",
                "correlation_id": correlation_id,
                "operation": operation,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "status": status,
                "api_key_id": api_key_id,
                "project_id": project_id,
                "ip_address": ip_address,
                "endpoint": endpoint,
                "http_method": http_method,
                "response_status": response_status,
                "timestamp": timestamp.isoformat(),
                "entry_hash": audit_entry.entry_hash,
                "metadata": metadata
            }
        )
        
        # Persist to database
        try:
            self.db.add(audit_entry)
            await self.db.flush()  # Get ID without committing
            
            audit_logger.debug(
                f"Audit log persisted: {audit_entry.id}",
                extra={"correlation_id": correlation_id, "audit_id": audit_entry.id}
            )
        
        except Exception as e:
            audit_logger.error(
                f"Failed to persist audit log: {e}",
                extra={"correlation_id": correlation_id, "error": str(e)},
                exc_info=True
            )
            # Don't fail the operation if audit logging fails
            # but log the error
        
        return audit_entry
    
    async def log_authentication_attempt(
        self,
        request: Request,
        success: bool,
        api_key_id: Optional[int] = None,
        project_id: Optional[int] = None,
        reason: Optional[str] = None
    ) -> AKMAuditLog:
        """
        Log authentication attempt.
        
        Args:
            request: FastAPI request
            success: Whether authentication succeeded
            api_key_id: ID of API key if authenticated
            project_id: Project ID if authenticated
            reason: Reason for failure if not successful
        """
        return await self.log_operation(
            operation="authenticate",
            resource_type="authentication",
            action="AUTH",
            request=request,
            api_key_id=api_key_id,
            project_id=project_id,
            status="success" if success else "denied",
            error_message=reason if not success else None,
            metadata={"authentication_result": success}
        )
    
    async def log_authorization_check(
        self,
        request: Request,
        required_scope: str,
        granted: bool,
        api_key_id: Optional[int] = None,
        project_id: Optional[int] = None,
        available_scopes: Optional[List[str]] = None
    ) -> AKMAuditLog:
        """
        Log authorization/permission check.
        
        Args:
            request: FastAPI request
            required_scope: Scope that was required
            granted: Whether access was granted
            api_key_id: ID of API key
            project_id: Project ID
            available_scopes: Scopes available to the key
        """
        return await self.log_operation(
            operation="authorize",
            resource_type="authorization",
            action="CHECK",
            request=request,
            api_key_id=api_key_id,
            project_id=project_id,
            status="success" if granted else "denied",
            metadata={
                "required_scope": required_scope,
                "granted": granted,
                "available_scopes": available_scopes
            }
        )
    
    @asynccontextmanager
    async def operation_context(self, correlation_id: Optional[str] = None):
        """
        Context manager for grouping related operations with same correlation ID.
        
        Usage:
            async with audit_logger.operation_context() as correlation_id:
                # All logs in this context share the correlation_id
                await audit_logger.log_operation(...)
        """
        # Generate or use provided correlation ID
        ctx_correlation_id = correlation_id or self.generate_correlation_id()
        
        # Store for nested operations
        previous_correlation_id = self.correlation_id
        self.correlation_id = ctx_correlation_id
        
        try:
            yield ctx_correlation_id
        finally:
            # Restore previous correlation ID
            self.correlation_id = previous_correlation_id


# Convenience functions for quick audit logging

async def log_audit(
    db: AsyncSession,
    operation: str,
    resource_type: str,
    action: str,
    **kwargs
) -> AKMAuditLog:
    """
    Quick audit logging without creating AuditLogger instance.
    
    Usage:
        await log_audit(
            db, 
            operation="create_project",
            resource_type="project",
            action="POST",
            resource_id="123",
            project_id=1,
            status="success"
        )
    """
    logger = AuditLogger(db)
    return await logger.log_operation(
        operation=operation,
        resource_type=resource_type,
        action=action,
        **kwargs
    )
