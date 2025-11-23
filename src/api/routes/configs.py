"""
API routes for API Key configuration and usage statistics.
"""

from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.database.repositories.api_key_repository import api_key_repository
from src.database.repositories.rate_limit_repository import rate_limit_repository
from src.database.models import AKMAPIKey
from src.api.auth_middleware import PermissionChecker
from src.api.models import APIKeyConfigUpdate, APIKeyConfigResponse, UsageStatsResponse

router = APIRouter(prefix="/keys", tags=["API Key Configuration"])


@router.get("/{key_id}/config", response_model=APIKeyConfigResponse)
async def get_key_config(
    key_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:keys:read"])),
    session: AsyncSession = Depends(get_session)
):
    """Get API key configuration"""
    key = await api_key_repository.get_by_id(session, key_id)
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found"
        )
    
    if not key.config:
        # Return default config if not set
        return APIKeyConfigResponse(
            rate_limit_per_minute=None,
            rate_limit_per_hour=None,
            rate_limit_per_day=None,
            rate_limit_per_month=None,
            allowed_ips=[],
            allowed_time_start=None,
            allowed_time_end=None
        )
    
    return key.config


@router.put("/{key_id}/config", response_model=APIKeyConfigResponse)
async def update_key_config(
    key_id: int,
    config_data: APIKeyConfigUpdate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:keys:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Update API key configuration"""
    key = await api_key_repository.get_by_id(session, key_id)
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found"
        )
    
    # Update config
    updated = await api_key_repository.update_config(
        session,
        key_id,
        rate_limit_per_minute=config_data.rate_limit_per_minute,
        rate_limit_per_hour=config_data.rate_limit_per_hour,
        rate_limit_per_day=config_data.rate_limit_per_day,
        rate_limit_per_month=config_data.rate_limit_per_month,
        allowed_ips=config_data.allowed_ips,
        allowed_time_start=config_data.allowed_time_start,
        allowed_time_end=config_data.allowed_time_end
    )
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update configuration"
        )
    
    return updated.config


@router.delete("/{key_id}/config", status_code=status.HTTP_204_NO_CONTENT)
async def reset_key_config(
    key_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:keys:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Reset API key configuration to defaults"""
    key = await api_key_repository.get_by_id(session, key_id)
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found"
        )
    
    # Reset to null values
    await api_key_repository.update_config(
        session,
        key_id,
        rate_limit_per_minute=None,
        rate_limit_per_hour=None,
        rate_limit_per_day=None,
        rate_limit_per_month=None,
        allowed_ips=[],
        allowed_time_start=None,
        allowed_time_end=None
    )
    
    return None


@router.get("/{key_id}/usage", response_model=UsageStatsResponse)
async def get_key_usage_stats(
    key_id: int,
    start_date: Optional[datetime] = Query(None, description="Start date for usage stats"),
    end_date: Optional[datetime] = Query(None, description="End date for usage stats"),
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:keys:read"])),
    session: AsyncSession = Depends(get_session)
):
    """Get API key usage statistics"""
    key = await api_key_repository.get_by_id(session, key_id)
    
    if not key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found"
        )
    
    stats = await rate_limit_repository.get_usage_stats(
        session,
        key_id,
        start_date=start_date,
        end_date=end_date
    )
    
    return stats
