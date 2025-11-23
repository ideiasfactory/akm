"""
API routes for Alert management.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.database.repositories.alert_repository import alert_repository
from src.database.models import AKMAPIKey
from src.api.auth_middleware import PermissionChecker
from src.api.models import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertHistoryResponse,
    AlertStatsResponse
)

router = APIRouter(prefix="/alerts", tags=["Alerts"])


# Alert Rules CRUD
@router.post("/rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:alerts:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Create a new alert rule"""
    rule = await alert_repository.create_rule(
        session,
        project_id=rule_data.project_id,
        api_key_id=rule_data.api_key_id,
        alert_type=rule_data.alert_type,
        condition_metric=rule_data.condition_metric,
        condition_operator=rule_data.condition_operator,
        condition_threshold=rule_data.condition_threshold,
        webhook_event_type=rule_data.webhook_event_type,
        cooldown_minutes=rule_data.cooldown_minutes,
        is_active=rule_data.is_active
    )
    
    return rule


@router.get("/rules", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    project_id: Optional[int] = None,
    api_key_id: Optional[int] = None,
    alert_type: Optional[str] = None,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:alerts:read"])),
    session: AsyncSession = Depends(get_session)
):
    """List alert rules"""
    rules = await alert_repository.list_rules(
        session,
        project_id=project_id,
        api_key_id=api_key_id,
        alert_type=alert_type,
        active_only=active_only,
        skip=skip,
        limit=limit
    )
    return rules


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:alerts:read"])),
    session: AsyncSession = Depends(get_session)
):
    """Get alert rule by ID"""
    rule = await alert_repository.get_rule(session, rule_id)
    
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule {rule_id} not found"
        )
    
    return rule


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: int,
    rule_data: AlertRuleUpdate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:alerts:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Update alert rule"""
    updated = await alert_repository.update_rule(
        session,
        rule_id,
        condition_metric=rule_data.condition_metric,
        condition_operator=rule_data.condition_operator,
        condition_threshold=rule_data.condition_threshold,
        webhook_event_type=rule_data.webhook_event_type,
        cooldown_minutes=rule_data.cooldown_minutes,
        is_active=rule_data.is_active
    )
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule {rule_id} not found"
        )
    
    return updated


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:alerts:delete"])),
    session: AsyncSession = Depends(get_session)
):
    """Delete alert rule"""
    success = await alert_repository.delete_rule(session, rule_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert rule {rule_id} not found"
        )
    
    return None


# Alert History
@router.get("/history", response_model=List[AlertHistoryResponse])
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


@router.get("/history/{history_id}", response_model=AlertHistoryResponse)
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


# Alert Statistics
@router.get("/stats", response_model=AlertStatsResponse)
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
