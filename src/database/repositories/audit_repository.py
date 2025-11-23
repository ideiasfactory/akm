"""
Audit Log Repository for querying audit trail.

Provides read-only access to audit logs with advanced filtering and integrity verification.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import AKMAuditLog, AKMAPIKey, AKMProject


class AuditLogRepository:
    """
    Read-only repository for audit log queries.
    
    Note: No update or delete methods - audit logs are immutable.
    """
    
    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def get_by_id(self, audit_id: int) -> Optional[AKMAuditLog]:
        """
        Get audit log entry by ID.
        
        Args:
            audit_id: Audit log ID
        
        Returns:
            Audit log entry or None
        """
        result = await self.db.execute(
            select(AKMAuditLog).where(AKMAuditLog.id == audit_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_correlation_id(self, correlation_id: str) -> List[AKMAuditLog]:
        """
        Get all audit log entries with same correlation ID.
        
        Useful for tracking all operations in a transaction.
        
        Args:
            correlation_id: Correlation ID to search for
        
        Returns:
            List of audit log entries ordered by timestamp
        """
        result = await self.db.execute(
            select(AKMAuditLog)
            .where(AKMAuditLog.correlation_id == correlation_id)
            .order_by(AKMAuditLog.timestamp)
        )
        return list(result.scalars().all())
    
    async def list_logs(
        self,
        project_id: Optional[int] = None,
        api_key_id: Optional[int] = None,
        operation: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        status: Optional[str] = None,
        ip_address: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AKMAuditLog]:
        """
        List audit logs with advanced filtering.
        
        Args:
            project_id: Filter by project ID
            api_key_id: Filter by API key ID
            operation: Filter by operation name
            resource_type: Filter by resource type
            resource_id: Filter by resource ID
            status: Filter by status (success, failure, denied)
            ip_address: Filter by IP address
            start_date: Filter logs after this timestamp
            end_date: Filter logs before this timestamp
            limit: Maximum number of results (max 1000)
            offset: Number of results to skip
        
        Returns:
            List of audit log entries ordered by timestamp (newest first)
        """
        # Build query with filters
        query = select(AKMAuditLog)
        
        # Apply filters
        filters = []
        
        if project_id is not None:
            filters.append(AKMAuditLog.project_id == project_id)
        
        if api_key_id is not None:
            filters.append(AKMAuditLog.api_key_id == api_key_id)
        
        if operation:
            filters.append(AKMAuditLog.operation == operation)
        
        if resource_type:
            filters.append(AKMAuditLog.resource_type == resource_type)
        
        if resource_id:
            filters.append(AKMAuditLog.resource_id == resource_id)
        
        if status:
            filters.append(AKMAuditLog.status == status)
        
        if ip_address:
            filters.append(AKMAuditLog.ip_address == ip_address)
        
        if start_date:
            filters.append(AKMAuditLog.timestamp >= start_date)
        
        if end_date:
            filters.append(AKMAuditLog.timestamp <= end_date)
        
        # Apply all filters
        if filters:
            query = query.where(and_(*filters))
        
        # Order by timestamp (newest first) and apply pagination
        query = query.order_by(desc(AKMAuditLog.timestamp))
        query = query.limit(min(limit, 1000)).offset(offset)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def count_logs(
        self,
        project_id: Optional[int] = None,
        api_key_id: Optional[int] = None,
        operation: Optional[str] = None,
        resource_type: Optional[str] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> int:
        """
        Count audit logs matching filters.
        
        Args:
            Same as list_logs (excluding pagination)
        
        Returns:
            Total count of matching audit logs
        """
        query = select(func.count(AKMAuditLog.id))
        
        # Apply same filters as list_logs
        filters = []
        
        if project_id is not None:
            filters.append(AKMAuditLog.project_id == project_id)
        
        if api_key_id is not None:
            filters.append(AKMAuditLog.api_key_id == api_key_id)
        
        if operation:
            filters.append(AKMAuditLog.operation == operation)
        
        if resource_type:
            filters.append(AKMAuditLog.resource_type == resource_type)
        
        if status:
            filters.append(AKMAuditLog.status == status)
        
        if start_date:
            filters.append(AKMAuditLog.timestamp >= start_date)
        
        if end_date:
            filters.append(AKMAuditLog.timestamp <= end_date)
        
        if filters:
            query = query.where(and_(*filters))
        
        result = await self.db.execute(query)
        return result.scalar_one()
    
    async def get_operations_summary(
        self,
        project_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get summary of operations grouped by operation name and status.
        
        Args:
            project_id: Filter by project ID
            start_date: Filter logs after this timestamp
            end_date: Filter logs before this timestamp
        
        Returns:
            List of dicts with operation, status, and count
        """
        query = select(
            AKMAuditLog.operation,
            AKMAuditLog.status,
            func.count(AKMAuditLog.id).label("count")
        )
        
        # Apply filters
        filters = []
        if project_id is not None:
            filters.append(AKMAuditLog.project_id == project_id)
        if start_date:
            filters.append(AKMAuditLog.timestamp >= start_date)
        if end_date:
            filters.append(AKMAuditLog.timestamp <= end_date)
        
        if filters:
            query = query.where(and_(*filters))
        
        # Group by operation and status
        query = query.group_by(AKMAuditLog.operation, AKMAuditLog.status)
        query = query.order_by(desc("count"))
        
        result = await self.db.execute(query)
        
        return [
            {
                "operation": row.operation,
                "status": row.status,
                "count": row.count
            }
            for row in result.all()
        ]
    
    async def get_resource_activity(
        self,
        resource_type: str,
        resource_id: str,
        limit: int = 50
    ) -> List[AKMAuditLog]:
        """
        Get activity history for a specific resource.
        
        Args:
            resource_type: Type of resource
            resource_id: ID of resource
            limit: Maximum number of results
        
        Returns:
            List of audit logs for the resource ordered by timestamp
        """
        result = await self.db.execute(
            select(AKMAuditLog)
            .where(
                and_(
                    AKMAuditLog.resource_type == resource_type,
                    AKMAuditLog.resource_id == resource_id
                )
            )
            .order_by(desc(AKMAuditLog.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_failed_operations(
        self,
        project_id: Optional[int] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[AKMAuditLog]:
        """
        Get recent failed operations.
        
        Args:
            project_id: Filter by project ID
            hours: Look back this many hours
            limit: Maximum number of results
        
        Returns:
            List of failed audit logs
        """
        # Calculate start time
        from datetime import timedelta, timezone
        start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        query = select(AKMAuditLog).where(
            and_(
                AKMAuditLog.status.in_(["failure", "denied"]),
                AKMAuditLog.timestamp >= start_time
            )
        )
        
        if project_id is not None:
            query = query.where(AKMAuditLog.project_id == project_id)
        
        query = query.order_by(desc(AKMAuditLog.timestamp)).limit(limit)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def verify_integrity(self, audit_id: int) -> Dict[str, Any]:
        """
        Verify integrity of an audit log entry.
        
        Args:
            audit_id: ID of audit log to verify
        
        Returns:
            Dict with verification result
        """
        audit_log = await self.get_by_id(audit_id)
        
        if not audit_log:
            return {
                "verified": False,
                "error": "Audit log not found"
            }
        
        is_valid = audit_log.verify_integrity()
        
        return {
            "verified": is_valid,
            "audit_id": audit_id,
            "correlation_id": audit_log.correlation_id,
            "stored_hash": audit_log.entry_hash,
            "calculated_hash": audit_log.calculate_hash(),
            "timestamp": audit_log.timestamp.isoformat(),
            "message": "Integrity verified" if is_valid else "INTEGRITY VIOLATION: Hash mismatch detected"
        }
    
    async def bulk_verify_integrity(
        self,
        project_id: Optional[int] = None,
        limit: int = 1000
    ) -> Dict[str, Any]:
        """
        Verify integrity of multiple audit logs.
        
        Args:
            project_id: Filter by project ID
            limit: Maximum number of logs to verify
        
        Returns:
            Summary of verification results
        """
        # Get recent logs
        logs = await self.list_logs(project_id=project_id, limit=limit)
        
        total = len(logs)
        verified = 0
        violations = []
        
        for log in logs:
            if log.verify_integrity():
                verified += 1
            else:
                violations.append({
                    "audit_id": log.id,
                    "correlation_id": log.correlation_id,
                    "operation": log.operation,
                    "timestamp": log.timestamp.isoformat(),
                    "stored_hash": log.entry_hash,
                    "calculated_hash": log.calculate_hash()
                })
        
        return {
            "total_verified": total,
            "passed": verified,
            "failed": len(violations),
            "integrity_score": (verified / total * 100) if total > 0 else 0,
            "violations": violations
        }
