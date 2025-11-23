"""
Pydantic models for Audit Log API.

Read-only models for querying and analyzing audit logs.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class AuditStatus(str, Enum):
    """Audit log status values."""
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


class AuditLogBase(BaseModel):
    """Base audit log fields."""
    
    correlation_id: str = Field(..., description="Unique correlation ID for grouping related operations")
    operation: str = Field(..., description="Operation name (e.g., 'create_api_key', 'delete_project')")
    action: str = Field(..., description="HTTP method or action type")
    resource_type: str = Field(..., description="Type of resource affected")
    resource_id: Optional[str] = Field(None, description="ID of affected resource")
    status: AuditStatus = Field(..., description="Operation status")
    
    # Request context
    endpoint: str = Field(..., description="API endpoint path")
    http_method: str = Field(..., description="HTTP method")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    
    # Response
    response_status: Optional[int] = Field(None, description="HTTP response status code")
    error_message: Optional[str] = Field(None, description="Error details if operation failed")
    
    # Timestamp
    timestamp: datetime = Field(..., description="Operation timestamp with microsecond precision")


class AuditLogDetail(AuditLogBase):
    """Detailed audit log with all fields."""
    
    id: int = Field(..., description="Audit log ID")
    entry_hash: str = Field(..., description="SHA-256 hash for integrity verification")
    
    # Authentication context
    api_key_id: Optional[int] = Field(None, description="ID of API key used")
    project_id: Optional[int] = Field(None, description="Project ID for multi-tenancy")
    
    # Request/Response payloads (sanitized)
    request_payload: Optional[Dict[str, Any]] = Field(None, description="Sanitized request body")
    response_payload: Optional[Dict[str, Any]] = Field(None, description="Sanitized response body")
    
    # Metadata
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    
    created_at: datetime = Field(..., description="Database insert timestamp")
    
    class Config:
        from_attributes = True


class AuditLogSummary(BaseModel):
    """Summary view of audit log (less detail for list views)."""
    
    id: int
    correlation_id: str
    operation: str
    resource_type: str
    resource_id: Optional[str]
    status: AuditStatus
    timestamp: datetime
    ip_address: Optional[str]
    api_key_id: Optional[int]
    project_id: Optional[int]
    response_status: Optional[int]
    
    class Config:
        from_attributes = True


class AuditLogListRequest(BaseModel):
    """Request model for listing audit logs with filters."""
    
    project_id: Optional[int] = Field(None, description="Filter by project ID")
    api_key_id: Optional[int] = Field(None, description="Filter by API key ID")
    operation: Optional[str] = Field(None, description="Filter by operation name")
    resource_type: Optional[str] = Field(None, description="Filter by resource type")
    resource_id: Optional[str] = Field(None, description="Filter by resource ID")
    status: Optional[AuditStatus] = Field(None, description="Filter by status")
    ip_address: Optional[str] = Field(None, description="Filter by IP address")
    start_date: Optional[datetime] = Field(None, description="Filter logs after this timestamp")
    end_date: Optional[datetime] = Field(None, description="Filter logs before this timestamp")
    limit: int = Field(100, ge=1, le=1000, description="Maximum number of results")
    offset: int = Field(0, ge=0, description="Number of results to skip")


class AuditLogListResponse(BaseModel):
    """Response model for audit log list."""
    
    total: int = Field(..., description="Total count of matching logs")
    limit: int = Field(..., description="Limit used in query")
    offset: int = Field(..., description="Offset used in query")
    logs: List[AuditLogSummary] = Field(..., description="List of audit logs")


class CorrelatedOperations(BaseModel):
    """Group of operations sharing same correlation ID."""
    
    correlation_id: str = Field(..., description="Shared correlation ID")
    operation_count: int = Field(..., description="Number of operations in group")
    operations: List[AuditLogSummary] = Field(..., description="Related operations")
    first_timestamp: datetime = Field(..., description="Timestamp of first operation")
    last_timestamp: datetime = Field(..., description="Timestamp of last operation")
    all_successful: bool = Field(..., description="True if all operations succeeded")


class OperationSummary(BaseModel):
    """Summary of operations grouped by type and status."""
    
    operation: str = Field(..., description="Operation name")
    status: AuditStatus = Field(..., description="Operation status")
    count: int = Field(..., description="Number of occurrences")


class AuditStatistics(BaseModel):
    """Statistics about audit logs."""
    
    total_operations: int = Field(..., description="Total number of operations")
    successful_operations: int = Field(..., description="Count of successful operations")
    failed_operations: int = Field(..., description="Count of failed operations")
    denied_operations: int = Field(..., description="Count of denied operations")
    unique_projects: int = Field(..., description="Number of unique projects")
    unique_api_keys: int = Field(..., description="Number of unique API keys")
    unique_ip_addresses: int = Field(..., description="Number of unique IP addresses")
    operations_by_type: List[OperationSummary] = Field(..., description="Operations grouped by type")
    start_date: Optional[datetime] = Field(None, description="Start of analysis period")
    end_date: Optional[datetime] = Field(None, description="End of analysis period")


class IntegrityVerification(BaseModel):
    """Result of audit log integrity verification."""
    
    verified: bool = Field(..., description="True if integrity check passed")
    audit_id: Optional[int] = Field(None, description="ID of verified audit log")
    correlation_id: Optional[str] = Field(None, description="Correlation ID of verified log")
    stored_hash: Optional[str] = Field(None, description="Hash stored in database")
    calculated_hash: Optional[str] = Field(None, description="Hash calculated from current data")
    timestamp: Optional[str] = Field(None, description="Timestamp of audit entry")
    message: str = Field(..., description="Verification result message")
    error: Optional[str] = Field(None, description="Error message if verification failed")


class BulkIntegrityVerification(BaseModel):
    """Result of bulk integrity verification."""
    
    total_verified: int = Field(..., description="Total number of logs verified")
    passed: int = Field(..., description="Number of logs that passed verification")
    failed: int = Field(..., description="Number of logs that failed verification")
    integrity_score: float = Field(..., description="Percentage of logs with valid integrity")
    violations: List[Dict[str, Any]] = Field(..., description="Details of integrity violations")


class ResourceActivity(BaseModel):
    """Activity history for a specific resource."""
    
    resource_type: str = Field(..., description="Type of resource")
    resource_id: str = Field(..., description="ID of resource")
    activity_count: int = Field(..., description="Number of activities")
    activities: List[AuditLogSummary] = Field(..., description="Activity history")
    first_activity: Optional[datetime] = Field(None, description="Timestamp of first activity")
    last_activity: Optional[datetime] = Field(None, description="Timestamp of last activity")
