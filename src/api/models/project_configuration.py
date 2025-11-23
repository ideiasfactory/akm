"""
Pydantic models for Project Configuration API.

Handles validation and serialization for dynamic project configurations.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, field_validator


class ProjectConfigurationBase(BaseModel):
    """Base model for project configuration"""
    
    cors_origins: Optional[List[str]] = Field(
        None,
        description="List of allowed CORS origins (URLs)",
        examples=[["https://example.com", "https://app.example.com"]]
    )
    default_rate_limit_per_minute: Optional[int] = Field(
        None,
        ge=1,
        description="Default rate limit per minute for API keys in this project"
    )
    default_rate_limit_per_hour: Optional[int] = Field(
        None,
        ge=1,
        description="Default rate limit per hour for API keys in this project"
    )
    default_rate_limit_per_day: Optional[int] = Field(
        None,
        ge=1,
        description="Default rate limit per day for API keys in this project"
    )
    default_rate_limit_per_month: Optional[int] = Field(
        None,
        ge=1,
        description="Default rate limit per month for API keys in this project"
    )
    ip_allowlist: Optional[List[str]] = Field(
        None,
        description="List of allowed IP addresses or CIDR ranges",
        examples=[["192.168.1.0/24", "10.0.0.1"]]
    )
    webhook_timeout_seconds: Optional[int] = Field(
        30,
        ge=1,
        le=300,
        description="Webhook timeout in seconds (1-300)"
    )
    webhook_max_retries: Optional[int] = Field(
        3,
        ge=0,
        le=10,
        description="Maximum webhook retry attempts (0-10)"
    )
    custom_sensitive_fields: Optional[List[str]] = Field(
        None,
        description="Additional field names to mask in logs/responses",
        examples=[["employee_id", "department_code"]]
    )
    config_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata for this configuration"
    )
    
    @field_validator('cors_origins')
    @classmethod
    def validate_cors_origins(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate CORS origins format"""
        if v is None:
            return v
        
        import re
        
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:[a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+'  # domain
            r'(?::\d+)?'  # optional port
            r'(?:/.*)?$'  # optional path
        )
        
        for origin in v:
            # Allow localhost with port
            if origin.startswith('http://localhost') or origin.startswith('http://127.0.0.1'):
                continue
            
            # Disallow wildcard
            if origin == '*':
                raise ValueError(
                    "Wildcard (*) is not allowed for CORS origins. "
                    "List each origin explicitly for security."
                )
            
            # Validate URL format
            if not url_pattern.match(origin):
                raise ValueError(f"Invalid origin format: {origin}")
        
        return v
    
    @field_validator('ip_allowlist')
    @classmethod
    def validate_ip_allowlist(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate IP addresses and CIDR ranges"""
        if v is None:
            return v
        
        import ipaddress
        
        for ip_str in v:
            try:
                # Try to parse as IP network (supports both single IPs and CIDR)
                ipaddress.ip_network(ip_str, strict=False)
            except ValueError as e:
                raise ValueError(
                    f"Invalid IP address or CIDR range: {ip_str}"
                ) from e
        
        return v
    
    @field_validator('custom_sensitive_fields')
    @classmethod
    def validate_sensitive_fields(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate custom sensitive field names"""
        if v is None:
            return v
        
        import re
        
        field_pattern = re.compile(r'^[a-z_][a-z0-9_]*$')
        
        for field_name in v:
            if not field_pattern.match(field_name):
                raise ValueError(
                    f"Invalid field name: {field_name}. "
                    "Use lowercase letters, numbers, and underscores only. "
                    "Must start with a letter or underscore."
                )
        
        return v


class ProjectConfigurationCreate(ProjectConfigurationBase):
    """Model for creating project configuration"""
    pass


class ProjectConfigurationUpdate(ProjectConfigurationBase):
    """Model for updating project configuration"""
    pass


class ProjectConfigurationResponse(ProjectConfigurationBase):
    """Model for project configuration response"""
    
    id: int = Field(description="Configuration ID")
    project_id: int = Field(description="Project ID")
    created_at: datetime = Field(description="Configuration creation timestamp")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")
    
    model_config = {
        "from_attributes": True,
        "json_schema_extra": {
            "examples": [
                {
                    "id": 1,
                    "project_id": 10,
                    "cors_origins": [
                        "https://example.com",
                        "https://app.example.com"
                    ],
                    "default_rate_limit_per_minute": 60,
                    "default_rate_limit_per_hour": 3600,
                    "default_rate_limit_per_day": 86400,
                    "default_rate_limit_per_month": None,
                    "ip_allowlist": ["192.168.1.0/24", "10.0.0.1"],
                    "webhook_timeout_seconds": 30,
                    "webhook_max_retries": 3,
                    "custom_sensitive_fields": ["employee_id"],
                    "config_metadata": {"environment": "production"},
                    "created_at": "2025-01-15T10:00:00Z",
                    "updated_at": "2025-01-15T14:30:00Z"
                }
            ]
        }
    }


class ProjectConfigurationDeleteResponse(BaseModel):
    """Response for configuration deletion"""
    
    success: bool = Field(description="Whether deletion was successful")
    message: str = Field(description="Deletion result message")
    project_id: int = Field(description="Project ID")
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "success": True,
                    "message": "Project configuration deleted successfully. Project will use global defaults.",
                    "project_id": 10
                }
            ]
        }
    }
