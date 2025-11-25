"""
Pydantic models for API Key endpoints.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from dataclasses import dataclass, asdict


class APIKeyCreate(BaseModel):
    """Request model for creating an API key"""
    project_id: int = Field(..., description="Project ID")
    name: str = Field(..., min_length=1, max_length=100, description="Key name")
    description: Optional[str] = Field(None, description="Key description")
    scopes: List[str] = Field(..., description="List of scope names")
    expires_at: Optional[datetime] = Field(None, description="Expiration datetime")


class APIKeyUpdate(BaseModel):
    """Request model for updating an API key"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_active: Optional[bool] = None
    expires_at: Optional[datetime] = None


class APIKeyScopesUpdate(BaseModel):
    """Request model for updating API key scopes"""
    scopes: List[str] = Field(..., description="Complete list of scope names to set")


class APIKeyResponse(BaseModel):
    """Response model for API key (without sensitive data)"""
    id: int
    project_id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    request_count: int
    scopes: List[str] = []
    
    class Config:
        from_attributes = True


class APIKeyCreateResponse(APIKeyResponse):
    """Response model for API key creation (includes plain key once)"""
    key: str = Field(..., description="Plain API key - save this, it won't be shown again!")


class ProjectInfo(BaseModel):
    """Project information embedded in responses"""
    id: int
    name: str
    is_active: bool


class APIKeyDetailedResponse(APIKeyResponse):
    """Detailed API key response with project info"""
    project: Optional[ProjectInfo] = None


class APIKeyValidationResponse(BaseModel):
    """Response model for API key validation"""
    service: str
    version: str
    docs_url: str
    message: str
    scopes_granted: List[str]

class APIKeyValidationRequest(BaseModel):
    """Request model for validate an API key"""
    client_api_key: str = Field(..., min_length=1, max_length=100, description="Client Key name")
    required_scopes: List[str] = Field(..., description="List of scope names to be validated")

