"""
Repository for Webhook operations.

Handles webhook creation, event subscriptions, and delivery management.
"""

import hmac
import hashlib
import json
import secrets
from typing import List, Optional, Dict
from datetime import datetime, timedelta

import httpx
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import (
    AKMWebhook,
    AKMWebhookEvent,
    AKMWebhookSubscription,
    AKMWebhookDelivery
)


class WebhookRepository:
    """Repository for webhook management and delivery"""
    
    async def create_webhook(
        self,
        session: AsyncSession,
        api_key_id: int,
        url: str,
        event_types: List[str],
        secret: Optional[str] = None,
        timeout_seconds: int = 30
    ) -> AKMWebhook:
        """Create webhook and subscribe to events"""
        # Generate secret if not provided
        if not secret:
            secret = secrets.token_urlsafe(32)
        
        webhook = AKMWebhook(
            api_key_id=api_key_id,
            url=url,
            secret=secret,
            is_active=True,
            timeout_seconds=timeout_seconds
        )
        
        session.add(webhook)
        await session.flush()
        
        # Create subscriptions
        for event_type in event_types:
            subscription = AKMWebhookSubscription(
                webhook_id=webhook.id,
                event_type=event_type,
                is_active=True
            )
            session.add(subscription)
        
        await session.commit()
        await session.refresh(webhook)
        
        return webhook
    
    async def get_by_id(
        self,
        session: AsyncSession,
        webhook_id: int
    ) -> Optional[AKMWebhook]:
        """Get webhook by ID"""
        stmt = select(AKMWebhook).where(AKMWebhook.id == webhook_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_with_subscriptions(
        self,
        session: AsyncSession,
        webhook_id: int
    ) -> Optional[AKMWebhook]:
        """Get webhook with subscriptions loaded"""
        stmt = select(AKMWebhook).where(
            AKMWebhook.id == webhook_id
        ).options(selectinload(AKMWebhook.subscriptions))
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_by_api_key(
        self,
        session: AsyncSession,
        api_key_id: int,
        active_only: bool = True
    ) -> List[AKMWebhook]:
        """List webhooks for an API key"""
        stmt = select(AKMWebhook).where(AKMWebhook.api_key_id == api_key_id)
        
        if active_only:
            stmt = stmt.where(AKMWebhook.is_active == True)
        
        stmt = stmt.options(selectinload(AKMWebhook.subscriptions))
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_webhook(
        self,
        session: AsyncSession,
        webhook_id: int,
        url: Optional[str] = None,
        is_active: Optional[bool] = None,
        timeout_seconds: Optional[int] = None,
        retry_policy: Optional[Dict] = None
    ) -> Optional[AKMWebhook]:
        """Update webhook configuration"""
        webhook = await self.get_by_id(session, webhook_id)
        
        if not webhook:
            return None
        
        if url is not None:
            webhook.url = url
        if is_active is not None:
            webhook.is_active = is_active
        if timeout_seconds is not None:
            webhook.timeout_seconds = timeout_seconds
        if retry_policy is not None:
            webhook.retry_policy = retry_policy
        
        webhook.updated_at = datetime.utcnow()
        
        await session.commit()
        await session.refresh(webhook)
        
        return webhook
    
    async def subscribe_to_event(
        self,
        session: AsyncSession,
        webhook_id: int,
        event_type: str
    ) -> bool:
        """Subscribe webhook to an event"""
        # Check if already subscribed
        stmt = select(AKMWebhookSubscription).where(
            and_(
                AKMWebhookSubscription.webhook_id == webhook_id,
                AKMWebhookSubscription.event_type == event_type
            )
        )
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            # Reactivate if inactive
            if not existing.is_active:
                existing.is_active = True
                await session.commit()
            return True
        
        # Create new subscription
        subscription = AKMWebhookSubscription(
            webhook_id=webhook_id,
            event_type=event_type,
            is_active=True
        )
        session.add(subscription)
        await session.commit()
        
        return True
    
    async def unsubscribe_from_event(
        self,
        session: AsyncSession,
        webhook_id: int,
        event_type: str
    ) -> bool:
        """Unsubscribe webhook from an event"""
        stmt = select(AKMWebhookSubscription).where(
            and_(
                AKMWebhookSubscription.webhook_id == webhook_id,
                AKMWebhookSubscription.event_type == event_type
            )
        )
        result = await session.execute(stmt)
        subscription = result.scalar_one_or_none()
        
        if not subscription:
            return False
        
        await session.delete(subscription)
        await session.commit()
        return True
    
    async def dispatch_event(
        self,
        session: AsyncSession,
        api_key_id: int,
        event_type: str,
        payload: Dict
    ):
        """Dispatch event to all subscribed webhooks"""
        # Find active webhooks subscribed to this event
        stmt = select(AKMWebhook).join(AKMWebhookSubscription).where(
            and_(
                AKMWebhook.api_key_id == api_key_id,
                AKMWebhook.is_active == True,
                AKMWebhookSubscription.event_type == event_type,
                AKMWebhookSubscription.is_active == True
            )
        )
        result = await session.execute(stmt)
        webhooks = result.scalars().all()
        
        # Create delivery record for each webhook
        deliveries = []
        for webhook in webhooks:
            delivery = AKMWebhookDelivery(
                webhook_id=webhook.id,
                event_type=event_type,
                payload=payload,
                status='pending',
                attempt_count=0
            )
            session.add(delivery)
            deliveries.append(delivery)
        
        await session.commit()
        
        # Process deliveries asynchronously
        for delivery in deliveries:
            await self._deliver_webhook(session, delivery.id)
    
    async def _deliver_webhook(
        self,
        session: AsyncSession,
        delivery_id: int
    ):
        """Deliver a single webhook"""
        # Get delivery and webhook
        stmt = select(AKMWebhookDelivery).where(AKMWebhookDelivery.id == delivery_id)
        result = await session.execute(stmt)
        delivery = result.scalar_one_or_none()
        
        if not delivery:
            return
        
        webhook = await self.get_by_id(session, delivery.webhook_id)
        if not webhook or not webhook.is_active:
            delivery.status = 'failed'
            delivery.response_body = 'Webhook inactive or deleted'
            await session.commit()
            return
        
        # Prepare payload
        payload = {
            "event_type": delivery.event_type,
            "data": delivery.payload,
            "timestamp": datetime.utcnow().isoformat(),
            "delivery_id": delivery.id
        }
        
        # Sign payload
        signature = self._sign_payload(payload, webhook.secret)
        
        # Send HTTP request
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Event-Type": delivery.event_type,
            "User-Agent": "AKM-Webhook/1.0"
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    webhook.url,
                    json=payload,
                    headers=headers,
                    timeout=webhook.timeout_seconds
                )
                
                delivery.http_status_code = response.status_code
                delivery.response_body = response.text[:1000]  # Limit size
                
                if response.is_success:
                    delivery.status = 'success'
                    delivery.delivered_at = datetime.utcnow()
                else:
                    delivery.status = 'failed'
                
        except httpx.TimeoutException:
            delivery.status = 'failed'
            delivery.response_body = f'Timeout after {webhook.timeout_seconds}s'
        except Exception as e:
            delivery.status = 'failed'
            delivery.response_body = str(e)[:1000]
        
        delivery.attempt_count += 1
        
        # Schedule retry if failed
        if delivery.status == 'failed' and delivery.attempt_count < webhook.retry_policy.get('max_retries', 3):
            backoff_seconds = webhook.retry_policy['backoff_seconds'][delivery.attempt_count - 1]
            delivery.next_retry_at = datetime.utcnow() + timedelta(seconds=backoff_seconds)
            delivery.status = 'retrying'
        
        await session.commit()
    
    async def process_retries(
        self,
        session: AsyncSession
    ) -> int:
        """Process pending webhook retries"""
        now = datetime.utcnow()
        
        stmt = select(AKMWebhookDelivery).where(
            and_(
                AKMWebhookDelivery.status == 'retrying',
                AKMWebhookDelivery.next_retry_at <= now
            )
        )
        result = await session.execute(stmt)
        pending_deliveries = result.scalars().all()
        
        for delivery in pending_deliveries:
            await self._deliver_webhook(session, delivery.id)
        
        return len(pending_deliveries)
    
    async def get_delivery_history(
        self,
        session: AsyncSession,
        webhook_id: int,
        limit: int = 50
    ) -> List[AKMWebhookDelivery]:
        """Get delivery history for a webhook"""
        stmt = select(AKMWebhookDelivery).where(
            AKMWebhookDelivery.webhook_id == webhook_id
        ).order_by(AKMWebhookDelivery.created_at.desc()).limit(limit)
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def delete_webhook(
        self,
        session: AsyncSession,
        webhook_id: int
    ) -> bool:
        """Delete webhook"""
        webhook = await self.get_by_id(session, webhook_id)
        
        if not webhook:
            return False
        
        await session.delete(webhook)
        await session.commit()
        return True
    
    def _sign_payload(self, payload: Dict, secret: str) -> str:
        """Sign payload with HMAC-SHA256"""
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        signature = hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    def verify_signature(self, payload: Dict, signature: str, secret: str) -> bool:
        """Verify webhook signature"""
        expected_signature = self._sign_payload(payload, secret)
        return hmac.compare_digest(signature, expected_signature)


# Singleton instance
webhook_repository = WebhookRepository()
