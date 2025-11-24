
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

AKM_SCOPES = [
    "akm:scopes:read",
    "akm:scopes:write",
    "akm:scopes:delete",
    "akm:scopes:delete_all",  # New operation for bulk delete all scopes
]

class BulkDeleteScopesRequest(BaseModel):
    """Request model for bulk deleting all scopes in a project"""
    confirm: str = Field(
        ...,
        min_length=10,
        description="Confirmation string, must be 'delete all scopes'"
    )

class ScopeCreate(BaseModel):
    """Request model for creating a scope"""
    scope_name: str = Field(
        ..., 
        min_length=1, 
        max_length=100,
        pattern=r'^[a-z0-9:*_-]+$',
        description="Scope name (e.g., akm:projects:read)"
    )
    description: Optional[str] = Field(None, description="Scope description")


class ScopeUpdate(BaseModel):
    """Request model for updating a scope"""
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ScopeResponse(BaseModel):
    """Response model for scope"""
    id: int
    scope_name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
