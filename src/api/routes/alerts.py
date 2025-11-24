"""
API routes for Alert management.

Alerts are now key-scoped following RESTful hierarchy:
- POST   /projects/{project_id}/keys/{key_id}/alerts
- GET    /projects/{project_id}/keys/{key_id}/alerts
- GET    /projects/{project_id}/keys/{key_id}/alerts/{alert_id}
- PUT    /projects/{project_id}/keys/{key_id}/alerts/{alert_id}
- DELETE /projects/{project_id}/keys/{key_id}/alerts/{alert_id}
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.database.repositories.alert_repository import alert_repository
from src.database.repositories.api_key_repository import api_key_repository
from src.database.models import AKMAPIKey
from src.api.auth_middleware import PermissionChecker
from src.api.models import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertHistoryResponse,
    AlertStatsResponse
)

router = APIRouter(tags=["Alerts"])


# Alert Rules CRUD - Key-scoped
@router.post("/projects/{project_id}/keys/{key_id}/alerts", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    project_id: int,
    key_id: int,
    rule_data: AlertRuleCreate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:alerts:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Create a new alert rule for an API key"""
    # Verify key exists and belongs to project
    key = await api_key_repository.get_by_id(session, key_id)
    if not key or key.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found in project {project_id}"
        )
    
    rule = await alert_repository.create_rule(
        session,
        api_key_id=key_id,
        rule_name=rule_data.rule_name,
        metric_type=rule_data.metric_type,
        threshold_value=rule_data.threshold_value,
        threshold_percentage=rule_data.threshold_percentage,
        comparison_operator=rule_data.comparison_operator,
        window_minutes=rule_data.window_minutes,
        cooldown_minutes=rule_data.cooldown_minutes,
        is_active=rule_data.is_active
    )
    
    return rule


@router.get("/projects/{project_id}/keys/{key_id}/alerts", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    project_id: int,
    key_id: int,
    alert_type: Optional[str] = None,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:alerts:read"])),
    session: AsyncSession = Depends(get_session)
):
    """List alert rules for an API key"""
    # Verify key exists and belongs to project
    key = await api_key_repository.get_by_id(session, key_id)
    if not key or key.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found in project {project_id}"
        )
    
    rules = await alert_repository.list_rules(
        session,
        api_key_id=key_id,
        alert_type=alert_type,
        active_only=active_only,
        skip=skip,
        limit=limit
    )
    return rules


@router.get("/projects/{project_id}/keys/{key_id}/alerts/{alert_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    project_id: int,
    key_id: int,
    alert_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:alerts:read"])),
    session: AsyncSession = Depends(get_session)
):
    """Get alert rule by ID"""
    # Verify key exists and belongs to project
    key = await api_key_repository.get_by_id(session, key_id)
    if not key or key.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found in project {project_id}"
        )
    
    rule = await alert_repository.get_rule(session, alert_id)
    
    if not rule or rule.api_key_id != key_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule {alert_id} not found for key {key_id}"
        )
    
    return rule


@router.put("/projects/{project_id}/keys/{key_id}/alerts/{alert_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    project_id: int,
    key_id: int,
    alert_id: int,
    rule_data: AlertRuleUpdate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:alerts:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Update alert rule"""
    # Verify key exists and belongs to project
    key = await api_key_repository.get_by_id(session, key_id)
    if not key or key.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found in project {project_id}"
        )
    
    rule = await alert_repository.get_rule(session, alert_id)
    if not rule or rule.api_key_id != key_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule {alert_id} not found for key {key_id}"
        )
    
    updated = await alert_repository.update_rule(
        session,
        alert_id,
        metric_type=rule_data.metric_type,
        threshold_value=rule_data.threshold_value,
        threshold_percentage=rule_data.threshold_percentage,
        comparison_operator=rule_data.comparison_operator,
        window_minutes=rule_data.window_minutes,
        cooldown_minutes=rule_data.cooldown_minutes,
        is_active=rule_data.is_active
    )
    
    return updated


@router.delete("/projects/{project_id}/keys/{key_id}/alerts/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    project_id: int,
    key_id: int,
    alert_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:alerts:delete"])),
    session: AsyncSession = Depends(get_session)
):
    """Delete alert rule"""
    # Verify key exists and belongs to project
    key = await api_key_repository.get_by_id(session, key_id)
    if not key or key.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found in project {project_id}"
        )
    
    rule = await alert_repository.get_rule(session, alert_id)
    if not rule or rule.api_key_id != key_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule {alert_id} not found for key {key_id}"
        )
    
    success = await alert_repository.delete_rule(session, alert_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule {alert_id} not found"
        )
    
    return None


# Alert History (Admin routes)
@router.get("/alerts/history", response_model=List[AlertHistoryResponse])
async def list_alert_history(
    rule_id: Optional[int] = None,
    start_date: Optional[datetime] = Query(None, description="Start date for history"),
    end_date: Optional[datetime] = Query(None, description="End date for history"),
    skip: int = 0,
    limit: int = 100,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:alerts:read"])),
    session: AsyncSession = Depends(get_session)
):
    """List alert history"""
    history = await alert_repository.get_alert_history(
        session,
        rule_id=rule_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit
    )
    return history


@router.get("/alerts/history/{history_id}", response_model=AlertHistoryResponse)
async def get_alert_history_item(
    history_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:alerts:read"])),
    session: AsyncSession = Depends(get_session)
):
    """Get alert history item by ID"""
    item = await alert_repository.get_history_item(session, history_id)
    
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert history {history_id} not found"
        )
    
    return item


# Alert Statistics (Admin routes)
@router.get("/alerts/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    project_id: Optional[int] = None,
    api_key_id: Optional[int] = None,
    start_date: Optional[datetime] = Query(None, description="Start date for stats"),
    end_date: Optional[datetime] = Query(None, description="End date for stats"),
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:alerts:read"])),
    session: AsyncSession = Depends(get_session)
):
    """Get alert statistics"""
    stats = await alert_repository.get_alert_stats(
        session,
        project_id=project_id,
        api_key_id=api_key_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return stats
