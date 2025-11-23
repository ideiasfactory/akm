"""
Repository for Alert Rule operations.

Handles alert rule management, evaluation, and history tracking.
"""

from typing import List, Optional, Dict
from datetime import datetime, timedelta

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import AKMAlertRule, AKMAlertHistory


class AlertRepository:
    """Repository for alert rule management"""
    
    async def create_rule(
        self,
        session: AsyncSession,
        api_key_id: int,
        rule_name: str,
        metric_type: str,
        threshold_value: int,
        comparison_operator: str,
        threshold_percentage: Optional[int] = None,
        window_minutes: int = 60,
        cooldown_minutes: int = 60
    ) -> AKMAlertRule:
        """Create a new alert rule"""
        rule = AKMAlertRule(
            api_key_id=api_key_id,
            rule_name=rule_name,
            metric_type=metric_type,
            threshold_value=threshold_value,
            threshold_percentage=threshold_percentage,
            comparison_operator=comparison_operator,
            window_minutes=window_minutes,
            is_active=True,
            cooldown_minutes=cooldown_minutes
        )
        
        session.add(rule)
        await session.commit()
        await session.refresh(rule)
        
        return rule
    
    async def get_by_id(
        self,
        session: AsyncSession,
        rule_id: int
    ) -> Optional[AKMAlertRule]:
        """Get alert rule by ID"""
        stmt = select(AKMAlertRule).where(AKMAlertRule.id == rule_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_by_api_key(
        self,
        session: AsyncSession,
        api_key_id: int,
        active_only: bool = True
    ) -> List[AKMAlertRule]:
        """List alert rules for an API key"""
        stmt = select(AKMAlertRule).where(AKMAlertRule.api_key_id == api_key_id)
        
        if active_only:
            stmt = stmt.where(AKMAlertRule.is_active == True)
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_rule(
        self,
        session: AsyncSession,
        rule_id: int,
        **kwargs
    ) -> Optional[AKMAlertRule]:
        """Update alert rule"""
        rule = await self.get_by_id(session, rule_id)
        
        if not rule:
            return None
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(rule, key) and value is not None:
                setattr(rule, key, value)
        
        rule.updated_at = datetime.utcnow()
        
        await session.commit()
        await session.refresh(rule)
        
        return rule
    
    async def delete_rule(
        self,
        session: AsyncSession,
        rule_id: int
    ) -> bool:
        """Delete alert rule"""
        rule = await self.get_by_id(session, rule_id)
        
        if not rule:
            return False
        
        await session.delete(rule)
        await session.commit()
        return True
    
    async def check_alerts(
        self,
        session: AsyncSession,
        api_key_id: int,
        metric_type: str,
        current_value: int,
        context: Optional[Dict] = None
    ) -> List[AKMAlertRule]:
        """
        Check if any alerts should be triggered for the given metric.
        Returns list of triggered alert rules.
        """
        now = datetime.utcnow()
        
        # Find active rules outside cooldown period
        stmt = select(AKMAlertRule).where(
            and_(
                AKMAlertRule.api_key_id == api_key_id,
                AKMAlertRule.metric_type == metric_type,
                AKMAlertRule.is_active == True,
                or_(
                    AKMAlertRule.last_triggered_at.is_(None),
                    AKMAlertRule.last_triggered_at < now - timedelta(minutes=AKMAlertRule.cooldown_minutes)
                )
            )
        )
        result = await session.execute(stmt)
        rules = result.scalars().all()
        
        triggered_rules = []
        
        for rule in rules:
            should_trigger = self._evaluate_rule(rule, current_value, context)
            
            if should_trigger:
                await self._trigger_alert(session, rule, current_value, context)
                triggered_rules.append(rule)
        
        return triggered_rules
    
    def _evaluate_rule(
        self,
        rule: AKMAlertRule,
        current_value: int,
        context: Optional[Dict] = None
    ) -> bool:
        """Evaluate if rule should trigger"""
        threshold = rule.threshold_value
        
        # Calculate percentage-based threshold if specified
        if rule.threshold_percentage and context:
            base_value = context.get('base_value', threshold)
            threshold = int(base_value * rule.threshold_percentage / 100)
        
        # Evaluate comparison
        operators = {
            '>=': lambda x, y: x >= y,
            '>': lambda x, y: x > y,
            '==': lambda x, y: x == y,
            '<': lambda x, y: x < y,
            '<=': lambda x, y: x <= y
        }
        
        op = operators.get(rule.comparison_operator)
        if not op:
            return False
        
        return op(current_value, threshold)
    
    async def _trigger_alert(
        self,
        session: AsyncSession,
        rule: AKMAlertRule,
        current_value: int,
        context: Optional[Dict] = None
    ):
        """Trigger an alert"""
        message = (
            f"Alert: {rule.rule_name} - "
            f"{rule.metric_type} is {current_value} "
            f"({rule.comparison_operator} {rule.threshold_value})"
        )
        
        # Create history record
        history = AKMAlertHistory(
            alert_rule_id=rule.id,
            api_key_id=rule.api_key_id,
            metric_value=current_value,
            threshold_value=rule.threshold_value,
            message=message
        )
        session.add(history)
        
        # Update last triggered timestamp
        rule.last_triggered_at = datetime.utcnow()
        
        await session.commit()
        await session.refresh(history)
        
        # Dispatch webhook event (will be handled by webhook repository)
        from src.database.repositories.webhook_repository import webhook_repository
        
        webhook_payload = {
            "alert_rule_id": rule.id,
            "rule_name": rule.rule_name,
            "metric_type": rule.metric_type,
            "current_value": current_value,
            "threshold_value": rule.threshold_value,
            "message": message,
            "context": context or {}
        }
        
        await webhook_repository.dispatch_event(
            session,
            rule.api_key_id,
            f"alert_{rule.metric_type}",
            webhook_payload
        )
    
    async def get_alert_history(
        self,
        session: AsyncSession,
        api_key_id: Optional[int] = None,
        rule_id: Optional[int] = None,
        limit: int = 100
    ) -> List[AKMAlertHistory]:
        """Get alert history"""
        stmt = select(AKMAlertHistory)
        
        if api_key_id:
            stmt = stmt.where(AKMAlertHistory.api_key_id == api_key_id)
        if rule_id:
            stmt = stmt.where(AKMAlertHistory.alert_rule_id == rule_id)
        
        stmt = stmt.order_by(AKMAlertHistory.created_at.desc()).limit(limit)
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_alert_stats(
        self,
        session: AsyncSession,
        api_key_id: int,
        days: int = 30
    ) -> Dict:
        """Get alert statistics for the past N days"""
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(AKMAlertHistory).where(
            and_(
                AKMAlertHistory.api_key_id == api_key_id,
                AKMAlertHistory.created_at >= cutoff
            )
        )
        result = await session.execute(stmt)
        history = result.scalars().all()
        
        if not history:
            return {
                "total_alerts": 0,
                "alerts_by_type": {},
                "recent_alerts": []
            }
        
        # Group by metric type
        alerts_by_type = {}
        for alert in history:
            stmt_rule = select(AKMAlertRule).where(AKMAlertRule.id == alert.alert_rule_id)
            result_rule = await session.execute(stmt_rule)
            rule = result_rule.scalar_one_or_none()
            
            if rule:
                metric_type = rule.metric_type
                alerts_by_type[metric_type] = alerts_by_type.get(metric_type, 0) + 1
        
        # Get recent alerts
        recent = sorted(history, key=lambda x: x.created_at, reverse=True)[:10]
        
        return {
            "total_alerts": len(history),
            "alerts_by_type": alerts_by_type,
            "recent_alerts": [
                {
                    "id": alert.id,
                    "rule_id": alert.alert_rule_id,
                    "message": alert.message,
                    "metric_value": alert.metric_value,
                    "created_at": alert.created_at.isoformat()
                }
                for alert in recent
            ]
        }


# Singleton instance
alert_repository = AlertRepository()
