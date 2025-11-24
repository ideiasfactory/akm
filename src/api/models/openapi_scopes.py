"""
Pydantic models for OpenAPI scope generation.
"""

from typing import List, Optional, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field, HttpUrl


class OpenAPISourceType(str, Enum):
    """Source type for OpenAPI specification"""
    URL = "url"
    FILE = "file"
    JSON = "json"


class ScopeGenerationStrategy(str, Enum):
    """Strategy for generating scopes from OpenAPI spec"""
    PATH_METHOD = "path_method"  # One scope per path + method (e.g., akm:users_get:read)
    PATH_RESOURCE = "path_resource"  # One scope per resource with CRUD (e.g., akm:users:read)
    TAG_BASED = "tag_based"  # One scope per tag + method (e.g., akm:users:read)
    OPERATION_ID = "operation_id"  # One scope per operationId (e.g., akm:getUser:execute)


class ScopeNamingConfig(BaseModel):
    """Configuration for scope naming"""
    namespace: str = Field(
        default="api",
        description="Namespace prefix for scopes (e.g., 'api', 'akm')",
        min_length=2,
        max_length=20
    )
    include_version: bool = Field(
        default=False,
        description="Include API version in scope name (e.g., api:v1:users:read)"
    )
    resource_naming: str = Field(
        default="path",
        description="How to name resources: 'path' (from URL path) or 'tag' (from OpenAPI tags)"
    )
    action_mapping: Dict[str, str] = Field(
        default_factory=lambda: {
            "GET": "read",
            "POST": "write",
            "PUT": "write",
            "PATCH": "write",
            "DELETE": "delete",
            "HEAD": "read",
            "OPTIONS": "read"
        },
        description="Map HTTP methods to scope actions"
    )


class OpenAPISourceRequest(BaseModel):
    """Request model for OpenAPI scope generation"""
    project_id: int = Field(
        ...,
        description="Project identifier for associating scope generation"
    )
    source_type: OpenAPISourceType = Field(
        ...,
        description="Type of source: url, file, or json"
    )
    source: Optional[str] = Field(
        None,
        description="URL or file path (required for url and file types)"
    )
    spec_data: Optional[Dict[str, Any]] = Field(
        None,
        description="OpenAPI spec as JSON object (required for json type)"
    )
    strategy: ScopeGenerationStrategy = Field(
        default=ScopeGenerationStrategy.PATH_RESOURCE,
        description="Strategy for generating scopes"
    )
    naming_config: ScopeNamingConfig = Field(
        default_factory=ScopeNamingConfig,
        description="Configuration for scope naming"
    )
    category: str = Field(
        default="api",
        description="Category for generated scopes"
    )
    generate_wildcards: bool = Field(
        default=True,
        description="Generate wildcard scopes for each resource (e.g., api:users:*)"
    )
    ignore_unknown_resources: bool = Field(
        default=True,
        description="Ignore importing scopes with unknown resources (e.g., brcds:unknown:read)"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "project_id": "my_project_123",
                "source_type": "url",
                "source": "https://api.example.com/openapi.json",
                "strategy": "path_resource",
                "naming_config": {
                    "namespace": "api",
                    "include_version": False,
                    "resource_naming": "path"
                },
                "category": "api",
                "generate_wildcards": True,
                "ignore_unknown_resources": True
            }
        }
    }


class GeneratedScope(BaseModel):
    """A single generated scope"""
    scope_name: str = Field(..., description="Generated scope name")
    description: str = Field(..., description="Human-readable description")
    category: str = Field(..., description="Scope category")
    is_active: bool = Field(default=True, description="Whether scope is active")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (path, method, tag, operationId)"
    )


class OpenAPIScopeGenerationResponse(BaseModel):
    """Response model for OpenAPI scope generation"""
    api_title: str = Field(..., description="API title from spec")
    api_version: str = Field(..., description="API version from spec")
    total_scopes: int = Field(..., description="Total number of scopes generated")
    strategy_used: ScopeGenerationStrategy = Field(..., description="Strategy used")
    scopes: List[GeneratedScope] = Field(..., description="Generated scopes")
    warnings: List[str] = Field(
        default_factory=list,
        description="Warnings during generation"
    )
    
    def to_bulk_format(self) -> Dict[str, Any]:
        """Convert to bulk import format"""
        return {
            "version": self.api_version,
            "scopes": [
                {
                    "scope_name": scope.scope_name,
                    "description": scope.description,
                    "category": scope.category,
                    "is_active": scope.is_active
                }
                for scope in self.scopes
            ]
        }


class OpenAPIAnalysisResponse(BaseModel):
    """Response model for OpenAPI spec analysis (preview)"""
    api_title: str
    api_version: str
    total_paths: int
    total_operations: int
    http_methods: List[str]
    tags: List[str]
    estimated_scopes_by_strategy: Dict[str, int] = Field(
        description="Estimated number of scopes for each strategy"
    )
    sample_scopes: Dict[str, List[str]] = Field(
        description="Sample scope names for each strategy (first 5)"
    )
