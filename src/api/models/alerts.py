"""
Pydantic models for Alert endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class AlertRuleCreate(BaseModel):
    """Request model for creating an alert rule"""
    rule_name: str = Field(..., min_length=1, max_length=100)
    metric_type: str = Field(..., description="Metric type (e.g., rate_limit, daily_limit)")
    threshold_value: int = Field(..., gt=0)
    threshold_percentage: Optional[int] = Field(None, ge=0, le=100, description="Threshold as percentage")
    comparison_operator: str = Field(..., pattern=r'^(>=|>|==|<|<=)$')
    window_minutes: int = Field(60, gt=0, description="Time window in minutes")
    cooldown_minutes: int = Field(60, gt=0, description="Cooldown period in minutes")


class AlertRuleUpdate(BaseModel):
    """Request model for updating an alert rule"""
    rule_name: Optional[str] = Field(None, min_length=1, max_length=100)
    threshold_value: Optional[int] = Field(None, gt=0)
    threshold_percentage: Optional[int] = Field(None, ge=0, le=100)
    comparison_operator: Optional[str] = Field(None, pattern=r'^(>=|>|==|<|<=)$')
    window_minutes: Optional[int] = Field(None, gt=0)
    cooldown_minutes: Optional[int] = Field(None, gt=0)
    is_active: Optional[bool] = None


class AlertRuleResponse(BaseModel):
    """Response model for alert rule"""
    id: int
    api_key_id: int
    rule_name: str
    metric_type: str
    threshold_value: int
    threshold_percentage: Optional[int]
    comparison_operator: str
    window_minutes: int
    is_active: bool
    cooldown_minutes: int
    last_triggered_at: Optional[datetime]
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class AlertHistoryResponse(BaseModel):
    """Response model for alert history"""
    id: int
    alert_rule_id: int
    api_key_id: int
    metric_value: int
    threshold_value: int
    message: Optional[str]
    webhook_delivery_id: Optional[int]
    created_at: datetime
    
    class Config:
        from_attributes = True


class AlertStatsResponse(BaseModel):
    """Response model for alert statistics"""
    total_alerts: int
    alerts_by_type: Dict[str, int]
    recent_alerts: List[Dict]
