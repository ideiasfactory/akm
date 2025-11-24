"""
Pydantic models for Project API endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProjectCreate(BaseModel):
    """Request model for creating a project"""
    name: str = Field(..., min_length=1, max_length=100, description="Project name")
    prefix: str = Field(..., min_length=1, max_length=20, description="Unique project prefix for namespacing")
    description: Optional[str] = Field(None, description="Project description")


class ProjectUpdate(BaseModel):
    """Request model for updating a project"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class ProjectResponse(BaseModel):
    """Response model for project"""
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class ProjectWithStats(ProjectResponse):
    """Project response with statistics"""
    active_keys_count: int
    total_keys_count: int
