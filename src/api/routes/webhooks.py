"""
API routes for Webhook management.

Webhooks are now key-scoped following RESTful hierarchy:
- POST   /projects/{project_id}/keys/{key_id}/webhooks
- GET    /projects/{project_id}/keys/{key_id}/webhooks
- GET    /projects/{project_id}/keys/{key_id}/webhooks/{webhook_id}
- PUT    /projects/{project_id}/keys/{key_id}/webhooks/{webhook_id}
- DELETE /projects/{project_id}/keys/{key_id}/webhooks/{webhook_id}
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.database.repositories.webhook_repository import webhook_repository
from src.database.repositories.api_key_repository import api_key_repository
from src.database.models import AKMAPIKey
from src.api.auth_middleware import PermissionChecker
from src.api.models import (
    WebhookCreate,
    WebhookUpdate,
    WebhookResponse,
    WebhookEventResponse,
    WebhookDeliveryResponse
)

router = APIRouter(tags=["Webhooks"])


# Webhook CRUD - Key-scoped
@router.post("/projects/{project_id}/keys/{key_id}/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    project_id: int,
    key_id: int,
    webhook_data: WebhookCreate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:webhooks:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Create a new webhook for an API key"""
    # Verify key exists and belongs to project
    key = await api_key_repository.get_by_id(session, key_id)
    if not key or key.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found in project {project_id}"
        )
    
    webhook = await webhook_repository.create_webhook(
        session,
        api_key_id=key_id,
        url=webhook_data.url,
        secret=webhook_data.secret,
        is_active=webhook_data.is_active
    )
    
    return webhook


@router.get("/projects/{project_id}/keys/{key_id}/webhooks", response_model=List[WebhookResponse])
async def list_webhooks(
    project_id: int,
    key_id: int,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:webhooks:read"])),
    session: AsyncSession = Depends(get_session)
):
    """List webhooks for an API key"""
    # Verify key exists and belongs to project
    key = await api_key_repository.get_by_id(session, key_id)
    if not key or key.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found in project {project_id}"
        )
    
    webhooks = await webhook_repository.list_webhooks(
        session,
        api_key_id=key_id,
        active_only=active_only,
        skip=skip,
        limit=limit
    )
    return webhooks


@router.get("/projects/{project_id}/keys/{key_id}/webhooks/{webhook_id}", response_model=WebhookResponse)
async def get_webhook(
    project_id: int,
    key_id: int,
    webhook_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:webhooks:read"])),
    session: AsyncSession = Depends(get_session)
):
    """Get webhook by ID"""
    # Verify key exists and belongs to project
    key = await api_key_repository.get_by_id(session, key_id)
    if not key or key.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found in project {project_id}"
        )
    
    webhook = await webhook_repository.get_webhook(session, webhook_id)
    
    if not webhook or webhook.api_key_id != key_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found for key {key_id}"
        )
    
    return webhook


@router.put("/projects/{project_id}/keys/{key_id}/webhooks/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    project_id: int,
    key_id: int,
    webhook_id: int,
    webhook_data: WebhookUpdate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:webhooks:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Update webhook"""
    # Verify key exists and belongs to project
    key = await api_key_repository.get_by_id(session, key_id)
    if not key or key.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found in project {project_id}"
        )
    
    webhook = await webhook_repository.get_webhook(session, webhook_id)
    if not webhook or webhook.api_key_id != key_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found for key {key_id}"
        )
    
    updated = await webhook_repository.update_webhook(
        session,
        webhook_id,
        url=webhook_data.url,
        secret=webhook_data.secret,
        is_active=webhook_data.is_active
    )
    
    return updated


@router.delete("/projects/{project_id}/keys/{key_id}/webhooks/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    project_id: int,
    key_id: int,
    webhook_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:webhooks:delete"])),
    session: AsyncSession = Depends(get_session)
):
    """Delete webhook"""
    # Verify key exists and belongs to project
    key = await api_key_repository.get_by_id(session, key_id)
    if not key or key.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found in project {project_id}"
        )
    
    webhook = await webhook_repository.get_webhook(session, webhook_id)
    if not webhook or webhook.api_key_id != key_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found for key {key_id}"
        )
    
    success = await webhook_repository.delete_webhook(session, webhook_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} not found"
        )
    
    return None


# Webhook Subscriptions
@router.post("/projects/{project_id}/keys/{key_id}/webhooks/{webhook_id}/subscriptions/{event_type}", status_code=status.HTTP_201_CREATED)
async def subscribe_to_event(
    project_id: int,
    key_id: int,
    webhook_id: int,
    event_type: str,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:webhooks:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Subscribe webhook to an event"""
    subscription = await webhook_repository.subscribe_webhook(
        session,
        webhook_id,
        event_type
    )
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Webhook {webhook_id} or event type '{event_type}' not found"
        )
    
    return {"message": f"Webhook {webhook_id} subscribed to {event_type}"}


@router.delete("/projects/{project_id}/keys/{key_id}/webhooks/{webhook_id}/subscriptions/{event_type}", status_code=status.HTTP_204_NO_CONTENT)
async def unsubscribe_from_event(
    project_id: int,
    key_id: int,
    webhook_id: int,
    event_type: str,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:webhooks:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Unsubscribe webhook from an event"""
    success = await webhook_repository.unsubscribe_webhook(
        session,
        webhook_id,
        event_type
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription not found"
        )
    
    return None


# Webhook Events (global)
@router.get("/webhooks/events/types", response_model=List[WebhookEventResponse])
async def list_event_types(
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:webhooks:read"])),
    session: AsyncSession = Depends(get_session)
):
    """List all available webhook event types"""
    events = await webhook_repository.list_event_types(session)
    return events


# Webhook Deliveries
@router.get("/projects/{project_id}/keys/{key_id}/webhooks/{webhook_id}/deliveries", response_model=List[WebhookDeliveryResponse])
async def list_deliveries(
    project_id: int,
    key_id: int,
    webhook_id: int,
    success_only: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:webhooks:read"])),
    session: AsyncSession = Depends(get_session)
):
    """List webhook deliveries"""
    deliveries = await webhook_repository.list_deliveries(
        session,
        webhook_id,
        success_only=success_only,
        skip=skip,
        limit=limit
    )
    return deliveries


@router.get("/webhooks/deliveries/{delivery_id}", response_model=WebhookDeliveryResponse)
async def get_delivery(
    delivery_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:webhooks:read"])),
    session: AsyncSession = Depends(get_session)
):
    """Get delivery details"""
    delivery = await webhook_repository.get_delivery(session, delivery_id)
    
    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery {delivery_id} not found"
        )
    
    return delivery


@router.post("/webhooks/deliveries/{delivery_id}/retry", response_model=WebhookDeliveryResponse)
async def retry_delivery(
    delivery_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:webhooks:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Retry failed webhook delivery"""
    delivery = await webhook_repository.get_delivery(session, delivery_id)
    
    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery {delivery_id} not found"
        )
    
    if delivery.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot retry successful delivery"
        )
    
    # Retry the delivery
    await webhook_repository.process_retries(session)
    
    # Get updated delivery
    updated = await webhook_repository.get_delivery(session, delivery_id)
    return updated
