"""
Rate limiting middleware with webhook notifications and alert checking.
"""

import time
from typing import Callable
from fastapi import Request, Response, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware

from src.database.connection import get_session
from src.database.repositories.rate_limit_repository import rate_limit_repository
from src.database.repositories.webhook_repository import webhook_repository
from src.database.repositories.alert_repository import alert_repository
from src.logging_config import get_logger

logger = get_logger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting API requests.
    
    Checks rate limits, daily/monthly limits, records metrics,
    and triggers webhooks/alerts when limits are reached.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with rate limiting checks"""
        start_time = time.time()
        
        # Skip rate limiting for non-API paths
        if not request.url.path.startswith("/api/"):
            return await call_next(request)
        
        # Skip if no API key (will be handled by auth middleware)
        api_key = getattr(request.state, "api_key", None)
        if not api_key:
            return await call_next(request)
        
        config = getattr(request.state, "api_key_config", None)
        if not config:
            # No config, no rate limiting
            return await call_next(request)
        
        # Get or create session
        async for session in get_session():
            try:
                # 1. Check rate limit per window
                if config.rate_limit_enabled and config.rate_limit_requests:
                    rate_check = await rate_limit_repository.check_and_increment(
                        session, api_key.id, config
                    )
                    
                    if not rate_check["allowed"]:
                        # Dispatch webhook event
                        await webhook_repository.dispatch_event(
                            session,
                            api_key.id,
                            "rate_limit_reached",
                            {
                                "current": rate_check["current"],
                                "limit": rate_check["limit"],
                                "reset_at": rate_check["reset_at"].isoformat() if rate_check["reset_at"] else None,
                                "retry_after": rate_check["retry_after"]
                            }
                        )
                        
                        logger.warning(
                            "Rate limit exceeded",
                            extra={
                                "api_key_id": api_key.id,
                                "current": rate_check["current"],
                                "limit": rate_check["limit"]
                            }
                        )
                        
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Rate limit exceeded. Try again in {rate_check['retry_after']} seconds.",
                            headers={
                                "Retry-After": str(rate_check["retry_after"]),
                                "X-RateLimit-Limit": str(rate_check["limit"]),
                                "X-RateLimit-Remaining": "0",
                                "X-RateLimit-Reset": str(int(rate_check["reset_at"].timestamp())) if rate_check["reset_at"] else ""
                            }
                        )
                    
                    # Add rate limit headers to response (will be added after call_next)
                    request.state.rate_limit_headers = {
                        "X-RateLimit-Limit": str(rate_check["limit"]),
                        "X-RateLimit-Remaining": str(max(0, rate_check["limit"] - rate_check["current"])),
                        "X-RateLimit-Reset": str(int(rate_check["reset_at"].timestamp())) if rate_check["reset_at"] else ""
                    }
                
                # 2. Check daily limit
                if config.daily_request_limit:
                    daily_check = await rate_limit_repository.check_daily_limit(
                        session, api_key.id, config.daily_request_limit
                    )
                    
                    if not daily_check["allowed"]:
                        await webhook_repository.dispatch_event(
                            session, api_key.id, "daily_limit_reached", daily_check
                        )
                        
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Daily request limit exceeded ({daily_check['limit']} requests).",
                            headers={"X-Daily-Limit": str(daily_check["limit"])}
                        )
                    
                    # Check for warning threshold (80%)
                    usage_percentage = (daily_check["current"] / daily_check["limit"]) * 100
                    if usage_percentage >= 80 and usage_percentage < 100:
                        # Check if we should trigger alerts
                        await alert_repository.check_alerts(
                            session,
                            api_key.id,
                            "daily_usage",
                            daily_check["current"],
                            context={"base_value": daily_check["limit"]}
                        )
                        
                        # Dispatch warning webhook
                        await webhook_repository.dispatch_event(
                            session,
                            api_key.id,
                            "daily_limit_warning",
                            {
                                "current": daily_check["current"],
                                "limit": daily_check["limit"],
                                "percentage": int(usage_percentage)
                            }
                        )
                
                # 3. Check monthly limit
                if config.monthly_request_limit:
                    monthly_check = await rate_limit_repository.check_monthly_limit(
                        session, api_key.id, config.monthly_request_limit
                    )
                    
                    if not monthly_check["allowed"]:
                        await webhook_repository.dispatch_event(
                            session, api_key.id, "monthly_limit_reached", monthly_check
                        )
                        
                        raise HTTPException(
                            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                            detail=f"Monthly request limit exceeded ({monthly_check['limit']} requests).",
                            headers={"X-Monthly-Limit": str(monthly_check["limit"])}
                        )
                    
                    # Check for warning threshold (80%)
                    usage_percentage = (monthly_check["current"] / monthly_check["limit"]) * 100
                    if usage_percentage >= 80 and usage_percentage < 100:
                        await alert_repository.check_alerts(
                            session,
                            api_key.id,
                            "monthly_usage",
                            monthly_check["current"],
                            context={"base_value": monthly_check["limit"]}
                        )
                        
                        await webhook_repository.dispatch_event(
                            session,
                            api_key.id,
                            "monthly_limit_warning",
                            {
                                "current": monthly_check["current"],
                                "limit": monthly_check["limit"],
                                "percentage": int(usage_percentage)
                            }
                        )
                
                # Process request
                response = await call_next(request)
                
                # 4. Record request metrics
                response_time = int((time.time() - start_time) * 1000)
                success = response.status_code < 400
                
                await rate_limit_repository.record_request(
                    session, api_key.id, success, response_time
                )
                
                # Add rate limit headers if available
                rate_limit_headers = getattr(request.state, "rate_limit_headers", {})
                for header, value in rate_limit_headers.items():
                    response.headers[header] = value
                
                # Check for high error rate
                if not success:
                    await alert_repository.check_alerts(
                        session,
                        api_key.id,
                        "error_rate",
                        1,  # This would need more sophisticated calculation
                        context={}
                    )
                
                return response
                
            except HTTPException:
                # Re-raise HTTP exceptions
                raise
            except Exception as e:
                logger.error(
                    f"Rate limit middleware error: {e}",
                    extra={
                        "api_key_id": api_key.id if api_key else None,
                        "error": str(e)
                    }
                )
                # Continue processing even if rate limiting fails
                return await call_next(request)
            finally:
                break  # Exit async generator


def add_rate_limit_middleware(app):
    """
    Add rate limiting middleware to FastAPI app.
    
    Usage:
        from src.middleware.rate_limit import add_rate_limit_middleware
        add_rate_limit_middleware(app)
    """
    app.add_middleware(RateLimitMiddleware)
