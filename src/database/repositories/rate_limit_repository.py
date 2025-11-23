"""
Repository for Rate Limit operations.

Handles rate limiting buckets, usage metrics, and limit checking.
"""

from typing import Optional, Dict
from datetime import datetime, timedelta, date

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    AKMRateLimitBucket,
    AKMUsageMetric,
    AKMAPIKeyConfig
)


class RateLimitRepository:
    """Repository for rate limiting and usage tracking"""
    
    async def check_and_increment(
        self,
        session: AsyncSession,
        api_key_id: int,
        config: AKMAPIKeyConfig
    ) -> Dict:
        """
        Check rate limit and increment counter atomically.
        
        Returns: {
            "allowed": bool,
            "current": int,
            "limit": int,
            "reset_at": datetime,
            "retry_after": int
        }
        """
        if not config.rate_limit_enabled:
            return {
                "allowed": True,
                "current": 0,
                "limit": 0,
                "reset_at": None,
                "retry_after": 0
            }
        
        now = datetime.utcnow()
        window_seconds = config.rate_limit_window_seconds or 60
        
        # Calculate window start (aligned to window size)
        seconds_since_epoch = int(now.timestamp())
        window_start_seconds = (seconds_since_epoch // window_seconds) * window_seconds
        window_start = datetime.utcfromtimestamp(window_start_seconds)
        window_end = window_start + timedelta(seconds=window_seconds)
        
        # Find or create bucket
        stmt = select(AKMRateLimitBucket).where(
            and_(
                AKMRateLimitBucket.api_key_id == api_key_id,
                AKMRateLimitBucket.window_start == window_start
            )
        )
        result = await session.execute(stmt)
        bucket = result.scalar_one_or_none()
        
        if not bucket:
            bucket = AKMRateLimitBucket(
                api_key_id=api_key_id,
                window_start=window_start,
                window_end=window_end,
                request_count=0
            )
            session.add(bucket)
            await session.flush()
        
        # Check limit
        current_count = bucket.request_count
        limit = config.rate_limit_requests
        allowed = current_count < limit
        
        if allowed:
            # Increment counter
            bucket.request_count += 1
            bucket.updated_at = now
            await session.commit()
        
        return {
            "allowed": allowed,
            "current": current_count + (1 if allowed else 0),
            "limit": limit,
            "reset_at": window_end,
            "retry_after": int((window_end - now).total_seconds())
        }
    
    async def check_daily_limit(
        self,
        session: AsyncSession,
        api_key_id: int,
        daily_limit: int
    ) -> Dict:
        """
        Check daily request limit.
        
        Returns: {
            "allowed": bool,
            "current": int,
            "limit": int,
            "remaining": int
        }
        """
        today = datetime.utcnow().date()
        
        stmt = select(func.sum(AKMUsageMetric.request_count)).where(
            and_(
                AKMUsageMetric.api_key_id == api_key_id,
                AKMUsageMetric.date == today
            )
        )
        result = await session.execute(stmt)
        current = result.scalar() or 0
        
        return {
            "allowed": current < daily_limit,
            "current": int(current),
            "limit": daily_limit,
            "remaining": max(0, daily_limit - int(current))
        }
    
    async def check_monthly_limit(
        self,
        session: AsyncSession,
        api_key_id: int,
        monthly_limit: int
    ) -> Dict:
        """
        Check monthly request limit.
        
        Returns: {
            "allowed": bool,
            "current": int,
            "limit": int,
            "remaining": int
        }
        """
        now = datetime.utcnow()
        month_start = now.replace(day=1).date()
        
        stmt = select(func.sum(AKMUsageMetric.request_count)).where(
            and_(
                AKMUsageMetric.api_key_id == api_key_id,
                AKMUsageMetric.date >= month_start
            )
        )
        result = await session.execute(stmt)
        current = result.scalar() or 0
        
        return {
            "allowed": current < monthly_limit,
            "current": int(current),
            "limit": monthly_limit,
            "remaining": max(0, monthly_limit - int(current))
        }
    
    async def record_request(
        self,
        session: AsyncSession,
        api_key_id: int,
        success: bool,
        response_time_ms: int
    ):
        """Record request in usage metrics"""
        now = datetime.utcnow()
        today = now.date()
        hour = now.hour
        
        # Find or create metric
        stmt = select(AKMUsageMetric).where(
            and_(
                AKMUsageMetric.api_key_id == api_key_id,
                AKMUsageMetric.date == today,
                AKMUsageMetric.hour == hour
            )
        )
        result = await session.execute(stmt)
        metric = result.scalar_one_or_none()
        
        if not metric:
            metric = AKMUsageMetric(
                api_key_id=api_key_id,
                date=today,
                hour=hour,
                request_count=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time_ms=0
            )
            session.add(metric)
        
        # Update counters
        metric.request_count += 1
        
        if success:
            metric.successful_requests += 1
        else:
            metric.failed_requests += 1
        
        # Update average response time (moving average)
        if metric.avg_response_time_ms:
            total_time = metric.avg_response_time_ms * (metric.request_count - 1)
            metric.avg_response_time_ms = int((total_time + response_time_ms) / metric.request_count)
        else:
            metric.avg_response_time_ms = response_time_ms
        
        metric.updated_at = now
        
        await session.commit()
    
    async def get_usage_stats(
        self,
        session: AsyncSession,
        api_key_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict:
        """Get usage statistics for a period"""
        if not start_date:
            start_date = (datetime.utcnow() - timedelta(days=30)).date()
        if not end_date:
            end_date = datetime.utcnow().date()
        
        stmt = select(AKMUsageMetric).where(
            and_(
                AKMUsageMetric.api_key_id == api_key_id,
                AKMUsageMetric.date >= start_date,
                AKMUsageMetric.date <= end_date
            )
        ).order_by(AKMUsageMetric.date, AKMUsageMetric.hour)
        
        result = await session.execute(stmt)
        metrics = result.scalars().all()
        
        if not metrics:
            return {
                "total_requests": 0,
                "successful_requests": 0,
                "failed_requests": 0,
                "avg_response_time_ms": 0,
                "error_rate": 0.0,
                "daily_breakdown": []
            }
        
        total_requests = sum(m.request_count for m in metrics)
        successful = sum(m.successful_requests for m in metrics)
        failed = sum(m.failed_requests for m in metrics)
        
        # Calculate weighted average response time
        total_weighted_time = sum(
            m.avg_response_time_ms * m.request_count 
            for m in metrics if m.avg_response_time_ms
        )
        avg_response_time = int(total_weighted_time / total_requests) if total_requests > 0 else 0
        
        error_rate = (failed / total_requests * 100) if total_requests > 0 else 0.0
        
        # Group by date
        daily_breakdown = {}
        for metric in metrics:
            date_key = metric.date.isoformat()
            if date_key not in daily_breakdown:
                daily_breakdown[date_key] = {
                    "date": date_key,
                    "requests": 0,
                    "successful": 0,
                    "failed": 0
                }
            daily_breakdown[date_key]["requests"] += metric.request_count
            daily_breakdown[date_key]["successful"] += metric.successful_requests
            daily_breakdown[date_key]["failed"] += metric.failed_requests
        
        return {
            "total_requests": total_requests,
            "successful_requests": successful,
            "failed_requests": failed,
            "avg_response_time_ms": avg_response_time,
            "error_rate": round(error_rate, 2),
            "daily_breakdown": list(daily_breakdown.values())
        }
    
    async def cleanup_old_buckets(
        self,
        session: AsyncSession,
        days_to_keep: int = 7
    ) -> int:
        """Clean up old rate limit buckets"""
        cutoff = datetime.utcnow() - timedelta(days=days_to_keep)
        
        stmt = select(AKMRateLimitBucket).where(
            AKMRateLimitBucket.window_end < cutoff
        )
        result = await session.execute(stmt)
        old_buckets = result.scalars().all()
        
        for bucket in old_buckets:
            await session.delete(bucket)
        
        await session.commit()
        return len(old_buckets)


# Singleton instance
rate_limit_repository = RateLimitRepository()
