"""
Audit Log API Routes (Read-Only).

Provides secure read-only access to audit logs with advanced filtering.
Requires special 'akm:audit:read' scope for access.
"""

from typing import Optional
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_async_session as get_db
from src.database.repositories.audit_repository import AuditLogRepository
from src.api.auth_middleware import PermissionChecker
from src.api.models.audit import (
    AuditLogDetail,
    AuditLogSummary,
    AuditLogListRequest,
    AuditLogListResponse,
    CorrelatedOperations,
    AuditStatistics,
    OperationSummary,
    IntegrityVerification,
    BulkIntegrityVerification,
    ResourceActivity,
    AuditStatus
)
from src.audit_logger import AuditLogger
from src.logging_config import get_logger

router = APIRouter(prefix="/audit", tags=["Audit Logs"])
logger = get_logger(__name__)

# Special scope required for audit log access
AUDIT_READ_SCOPE = "akm:audit:read"


@router.get(
    "/logs/{audit_id}",
    response_model=AuditLogDetail,
    summary="Get audit log by ID",
    description="Retrieve detailed information about a specific audit log entry. Requires 'akm:audit:read' scope."
)
async def get_audit_log(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(PermissionChecker([AUDIT_READ_SCOPE]))
):
    """Get audit log entry by ID."""
    repo = AuditLogRepository(db)
    audit_log = await repo.get_by_id(audit_id)
    
    if not audit_log:
        raise HTTPException(status_code=404, detail="Audit log not found")
    
    return audit_log


@router.get(
    "/logs",
    response_model=AuditLogListResponse,
    summary="List audit logs with filters",
    description="Query audit logs with advanced filtering options. Requires 'akm:audit:read' scope."
)
async def list_audit_logs(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    api_key_id: Optional[int] = Query(None, description="Filter by API key ID"),
    operation: Optional[str] = Query(None, description="Filter by operation name"),
    resource_type: Optional[str] = Query(None, description="Filter by resource type"),
    resource_id: Optional[str] = Query(None, description="Filter by resource ID"),
    status: Optional[AuditStatus] = Query(None, description="Filter by status"),
    ip_address: Optional[str] = Query(None, description="Filter by IP address"),
    start_date: Optional[datetime] = Query(None, description="Filter logs after this timestamp (ISO 8601)"),
    end_date: Optional[datetime] = Query(None, description="Filter logs before this timestamp (ISO 8601)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    db: AsyncSession = Depends(get_db),
    auth: dict = Depends(PermissionChecker([AUDIT_READ_SCOPE]))
):
    """
    List audit logs with filtering and pagination.
    
    **Filtering Options:**
    - Project ID: Filter by specific project
    - API Key ID: Filter by specific API key
    - Operation: Filter by operation name (e.g., 'create_api_key')
    - Resource Type: Filter by resource type (e.g., 'api_key', 'project')
    - Status: Filter by operation status (success, failure, denied)
    - Date Range: Filter by timestamp range
    
    **Pagination:**
    - Use limit and offset for pagination
    - Maximum limit is 1000 per request
    """
    repo = AuditLogRepository(db)
    
    # Get logs with filters
    logs = await repo.list_logs(
        project_id=project_id,
        api_key_id=api_key_id,
        operation=operation,
        resource_type=resource_type,
        resource_id=resource_id,
        status=status.value if status else None,
        ip_address=ip_address,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset
    )
    
    # Get total count
    total = await repo.count_logs(
        project_id=project_id,
        api_key_id=api_key_id,
        operation=operation,
        resource_type=resource_type,
        status=status.value if status else None,
        start_date=start_date,
        end_date=end_date
    )
    
    # Log audit query
    audit_logger = AuditLogger(db)
    await audit_logger.log_operation(
        operation="query_audit_logs",
        resource_type="audit_logs",
        action="GET",
        api_key_id=auth.get("api_key_id"),
        project_id=auth.get("project_id"),
        status="success",
        metadata={
            "filters": {
                "project_id": project_id,
                "operation": operation,
                "status": status.value if status else None,
                "date_range": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                }
            },
            "result_count": len(logs),
            "total_count": total
        }
    )
    await db.commit()
    
    return AuditLogListResponse(
        total=total,
        limit=limit,
        offset=offset,
        logs=[AuditLogSummary.model_validate(log) for log in logs]
    )


@router.get(
    "/correlation/{correlation_id}",
    response_model=CorrelatedOperations,
    summary="Get correlated operations",
    description="Get all operations that share the same correlation ID (related operations in a transaction)."
)
async def get_correlated_operations(
    correlation_id: str,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(PermissionChecker([AUDIT_READ_SCOPE]))
):
    """Get all audit logs with the same correlation ID."""
    repo = AuditLogRepository(db)
    logs = await repo.get_by_correlation_id(correlation_id)
    
    if not logs:
        raise HTTPException(status_code=404, detail="No logs found with this correlation ID")
    
    # Calculate metadata
    timestamps = [log.timestamp for log in logs]
    all_successful = all(log.status == "success" for log in logs)
    
    return CorrelatedOperations(
        correlation_id=correlation_id,
        operation_count=len(logs),
        operations=[AuditLogSummary.model_validate(log) for log in logs],
        first_timestamp=min(timestamps),
        last_timestamp=max(timestamps),
        all_successful=all_successful
    )


@router.get(
    "/resource/{resource_type}/{resource_id}",
    response_model=ResourceActivity,
    summary="Get resource activity history",
    description="Get complete activity history for a specific resource."
)
async def get_resource_activity(
    resource_type: str,
    resource_id: str,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of activities"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(PermissionChecker([AUDIT_READ_SCOPE]))
):
    """Get activity history for a specific resource."""
    repo = AuditLogRepository(db)
    activities = await repo.get_resource_activity(resource_type, resource_id, limit)
    
    if not activities:
        raise HTTPException(
            status_code=404, 
            detail=f"No activity found for {resource_type} with ID {resource_id}"
        )
    
    timestamps = [log.timestamp for log in activities]
    
    return ResourceActivity(
        resource_type=resource_type,
        resource_id=resource_id,
        activity_count=len(activities),
        activities=[AuditLogSummary.model_validate(log) for log in activities],
        first_activity=min(timestamps),
        last_activity=max(timestamps)
    )


@router.get(
    "/statistics",
    response_model=AuditStatistics,
    summary="Get audit statistics",
    description="Get statistical summary of audit logs over a time period."
)
async def get_audit_statistics(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    hours: int = Query(24, ge=1, le=8760, description="Look back this many hours (max 1 year)"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(PermissionChecker([AUDIT_READ_SCOPE]))
):
    """Get audit statistics for a time period."""
    repo = AuditLogRepository(db)
    
    # Calculate date range
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(hours=hours)
    
    # Get operations summary
    operations_summary = await repo.get_operations_summary(
        project_id=project_id,
        start_date=start_date,
        end_date=end_date
    )
    
    # Get all logs for counting
    all_logs = await repo.list_logs(
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        limit=10000  # High limit for statistics
    )
    
    # Calculate statistics
    total = len(all_logs)
    successful = sum(1 for log in all_logs if log.status == "success")
    failed = sum(1 for log in all_logs if log.status == "failure")
    denied = sum(1 for log in all_logs if log.status == "denied")
    
    unique_projects = len(set(log.project_id for log in all_logs if log.project_id))
    unique_keys = len(set(log.api_key_id for log in all_logs if log.api_key_id))
    unique_ips = len(set(log.ip_address for log in all_logs if log.ip_address))
    
    return AuditStatistics(
        total_operations=total,
        successful_operations=successful,
        failed_operations=failed,
        denied_operations=denied,
        unique_projects=unique_projects,
        unique_api_keys=unique_keys,
        unique_ip_addresses=unique_ips,
        operations_by_type=[
            OperationSummary(
                operation=op["operation"],
                status=AuditStatus(op["status"]),
                count=op["count"]
            )
            for op in operations_summary
        ],
        start_date=start_date,
        end_date=end_date
    )


@router.get(
    "/failed",
    response_model=list[AuditLogSummary],
    summary="Get recent failed operations",
    description="Get list of recent failed or denied operations for troubleshooting."
)
async def get_failed_operations(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    hours: int = Query(24, ge=1, le=168, description="Look back this many hours (max 1 week)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(PermissionChecker([AUDIT_READ_SCOPE]))
):
    """Get recent failed operations."""
    repo = AuditLogRepository(db)
    failed_ops = await repo.get_failed_operations(
        project_id=project_id,
        hours=hours,
        limit=limit
    )
    
    return [AuditLogSummary.model_validate(log) for log in failed_ops]


@router.get(
    "/integrity/verify/{audit_id}",
    response_model=IntegrityVerification,
    summary="Verify audit log integrity",
    description="Verify the integrity of a specific audit log entry using its hash."
)
async def verify_audit_integrity(
    audit_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(PermissionChecker([AUDIT_READ_SCOPE]))
):
    """Verify integrity of a single audit log entry."""
    repo = AuditLogRepository(db)
    verification = await repo.verify_integrity(audit_id)
    
    return IntegrityVerification(**verification)


@router.get(
    "/integrity/bulk-verify",
    response_model=BulkIntegrityVerification,
    summary="Bulk verify audit log integrity",
    description="Verify integrity of multiple audit logs to detect tampering."
)
async def bulk_verify_integrity(
    project_id: Optional[int] = Query(None, description="Filter by project ID"),
    limit: int = Query(1000, ge=1, le=10000, description="Number of logs to verify"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(PermissionChecker([AUDIT_READ_SCOPE]))
):
    """Bulk verify integrity of audit logs."""
    repo = AuditLogRepository(db)
    verification = await repo.bulk_verify_integrity(
        project_id=project_id,
        limit=limit
    )
    
    # Log if integrity violations found
    if verification["failed"] > 0:
        logger.critical(
            f"AUDIT INTEGRITY VIOLATION: {verification['failed']} logs failed verification",
            extra={
                "total_verified": verification["total_verified"],
                "failed_count": verification["failed"],
                "integrity_score": verification["integrity_score"],
                "violations": verification["violations"]
            }
        )
    
    return BulkIntegrityVerification(**verification)
