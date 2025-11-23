"""
Pydantic models for API Key Configuration endpoints.
"""

from datetime import time
from typing import Optional, List, Dict
from pydantic import BaseModel, Field, field_validator


class APIKeyConfigUpdate(BaseModel):
    """Request model for updating API key configuration"""
    
    # Rate limiting
    rate_limit_enabled: Optional[bool] = None
    rate_limit_requests: Optional[int] = Field(None, gt=0, description="Requests per window")
    rate_limit_window_seconds: Optional[int] = Field(None, gt=0, le=3600, description="Window size in seconds")
    
    # Daily/Monthly limits
    daily_request_limit: Optional[int] = Field(None, gt=0)
    monthly_request_limit: Optional[int] = Field(None, gt=0)
    
    # IP Whitelist
    ip_whitelist_enabled: Optional[bool] = None
    allowed_ips: Optional[List[str]] = Field(None, description="List of IPs or CIDR blocks")
    
    # Time restrictions
    allowed_time_start: Optional[time] = Field(None, description="Start time (e.g., 08:00)")
    allowed_time_end: Optional[time] = Field(None, description="End time (e.g., 18:00)")
    
    @field_validator('allowed_ips')
    @classmethod
    def validate_ips(cls, v):
        if v is not None and len(v) == 0:
            return None
        return v


class APIKeyConfigResponse(BaseModel):
    """Response model for API key configuration"""
    id: int
    api_key_id: int
    
    rate_limit_enabled: bool
    rate_limit_requests: Optional[int]
    rate_limit_window_seconds: Optional[int]
    
    daily_request_limit: Optional[int]
    monthly_request_limit: Optional[int]
    
    ip_whitelist_enabled: bool
    allowed_ips: Optional[List[str]]
    
    allowed_time_start: Optional[time]
    allowed_time_end: Optional[time]
    
    class Config:
        from_attributes = True


class UsageStatsResponse(BaseModel):
    """Response model for usage statistics"""
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: int
    error_rate: float
    daily_breakdown: List[Dict]
