"""
Pydantic models for Webhook endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, HttpUrl


class WebhookCreate(BaseModel):
    """Request model for creating a webhook"""
    url: str = Field(..., description="Webhook URL")
    event_types: List[str] = Field(..., min_items=1, description="Event types to subscribe to")
    timeout_seconds: int = Field(30, gt=0, le=120, description="Request timeout in seconds")


class WebhookUpdate(BaseModel):
    """Request model for updating a webhook"""
    url: Optional[str] = None
    is_active: Optional[bool] = None
    timeout_seconds: Optional[int] = Field(None, gt=0, le=120)
    retry_policy: Optional[Dict] = None


class WebhookSubscriptionUpdate(BaseModel):
    """Request model for updating webhook subscriptions"""
    event_types: List[str] = Field(..., description="Complete list of event types")


class WebhookResponse(BaseModel):
    """Response model for webhook"""
    id: int
    api_key_id: int
    url: str
    is_active: bool
    timeout_seconds: int
    retry_policy: Dict
    created_at: datetime
    updated_at: Optional[datetime]
    event_types: List[str] = []
    
    class Config:
        from_attributes = True


class WebhookEventResponse(BaseModel):
    """Response model for webhook event"""
    id: int
    event_type: str
    description: Optional[str]
    is_active: bool
    payload_schema: Optional[Dict]
    created_at: datetime
    
    class Config:
        from_attributes = True


class WebhookDeliveryResponse(BaseModel):
    """Response model for webhook delivery"""
    id: int
    webhook_id: int
    event_type: str
    payload: Dict
    status: str
    http_status_code: Optional[int]
    response_body: Optional[str]
    attempt_count: int
    next_retry_at: Optional[datetime]
    delivered_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True
