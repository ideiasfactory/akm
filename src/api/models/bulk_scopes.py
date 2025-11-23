"""
Pydantic models for bulk scope operations.
"""

from typing import List
from pydantic import BaseModel, Field, field_validator
import re


class BulkScopeItem(BaseModel):
    """Individual scope item for bulk operations"""
    scope_name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Unique scope identifier in format: namespace:resource:action"
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Human-readable description of the scope"
    )
    category: str = Field(
        ...,
        description="Scope category for organization"
    )
    is_active: bool = Field(
        default=True,
        description="Whether the scope is active"
    )
    
    @field_validator('scope_name')
    @classmethod
    def validate_scope_name(cls, v: str) -> str:
        """Validate scope name format"""
        pattern = r'^[a-z0-9]+:[a-z0-9_]+:[a-z0-9_*]+$'
        if not re.match(pattern, v):
            raise ValueError(
                f"Invalid scope name format: '{v}'. "
                "Expected format: 'namespace:resource:action' (e.g., 'akm:projects:read')"
            )
        return v
    
    @field_validator('category')
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate category is one of allowed values"""
        allowed = ['projects', 'keys', 'scopes', 'webhooks', 'alerts', 'usage', 'admin', 'system']
        if v not in allowed:
            raise ValueError(
                f"Invalid category: '{v}'. "
                f"Allowed values: {', '.join(allowed)}"
            )
        return v


class BulkScopesRequest(BaseModel):
    """Request model for bulk scope operations"""
    version: str = Field(
        ...,
        pattern=r'^\d+\.\d+\.\d+$',
        description="Schema version (semantic versioning)"
    )
    scopes: List[BulkScopeItem] = Field(
        ...,
        min_length=1,
        description="List of scopes to upsert"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "version": "1.0.0",
                "scopes": [
                    {
                        "scope_name": "akm:projects:read",
                        "description": "View projects and their details",
                        "category": "projects",
                        "is_active": True
                    },
                    {
                        "scope_name": "akm:projects:write",
                        "description": "Create and update projects",
                        "category": "projects",
                        "is_active": True
                    }
                ]
            }
        }
    }


class BulkScopesResponse(BaseModel):
    """Response model for bulk scope operations"""
    total_processed: int = Field(
        ...,
        description="Total number of scopes processed"
    )
    created: int = Field(
        ...,
        description="Number of new scopes created"
    )
    updated: int = Field(
        ...,
        description="Number of existing scopes updated"
    )
    skipped: int = Field(
        default=0,
        description="Number of scopes skipped (no changes)"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="List of error messages if any"
    )
    scope_names: List[str] = Field(
        default_factory=list,
        description="List of processed scope names"
    )
