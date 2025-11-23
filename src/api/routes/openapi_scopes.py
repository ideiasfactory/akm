"""
API routes for OpenAPI/Swagger scope generation.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.database.repositories.scope_repository import scope_repository
from src.database.models import AKMAPIKey
from src.api.auth_middleware import PermissionChecker
from src.api.models import (
    OpenAPISourceType,
    ScopeGenerationStrategy,
    OpenAPISourceRequest,
    OpenAPIScopeGenerationResponse,
    OpenAPIAnalysisResponse,
    BulkScopesResponse,
)
from src.services import openapi_scope_generator

router = APIRouter(prefix="/scopes/openapi", tags=["OpenAPI Scope Generation"])


@router.post("/analyze", response_model=OpenAPIAnalysisResponse)
async def analyze_openapi_spec(
    request: OpenAPISourceRequest,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:read"]))
):
    """
    Analyze OpenAPI/Swagger specification and preview scope generation.
    
    This endpoint analyzes the spec and returns statistics about what scopes
    would be generated for each strategy, without actually generating them.
    """
    try:
        # Load spec
        spec = await openapi_scope_generator.load_spec(
            request.source_type,
            request.source,
            request.spec_data
        )
        
        # Analyze
        analysis = openapi_scope_generator.analyze_spec(spec)
        
        return analysis
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to analyze OpenAPI spec: {str(e)}"
        )


@router.post("/generate", response_model=OpenAPIScopeGenerationResponse)
async def generate_scopes_from_openapi(
    request: OpenAPISourceRequest,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:read"]))
):
    """
    Generate scopes from OpenAPI/Swagger specification.
    
    Supports multiple input methods:
    - URL: Fetch spec from a URL (e.g., https://api.example.com/openapi.json)
    - File: Load spec from uploaded file (use /generate/file endpoint)
    - JSON: Provide spec directly in request body
    
    Supports multiple generation strategies:
    - path_resource: One scope per resource with CRUD actions (recommended)
    - path_method: One scope per path + HTTP method combination
    - tag_based: One scope per OpenAPI tag + action
    - operation_id: One scope per operationId
    """
    try:
        # Load spec
        spec = await openapi_scope_generator.load_spec(
            request.source_type,
            request.source,
            request.spec_data
        )
        
        # Generate scopes
        result = openapi_scope_generator.generate_scopes(
            spec,
            request.strategy,
            request.naming_config,
            request.category,
            request.generate_wildcards
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to generate scopes: {str(e)}"
        )


@router.post("/generate/file", response_model=OpenAPIScopeGenerationResponse)
async def generate_scopes_from_file(
    file: UploadFile = File(..., description="OpenAPI spec file (JSON or YAML)"),
    strategy: ScopeGenerationStrategy = ScopeGenerationStrategy.PATH_RESOURCE,
    namespace: str = "api",
    category: str = "api",
    generate_wildcards: bool = True,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:read"]))
):
    """
    Generate scopes from uploaded OpenAPI/Swagger file.
    
    Accepts both JSON and YAML formats.
    """
    try:
        # Read file content
        content = await file.read()
        
        # Try to parse as JSON or YAML
        import json
        import yaml
        
        try:
            spec = json.loads(content)
        except json.JSONDecodeError:
            try:
                spec = yaml.safe_load(content)
            except yaml.YAMLError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid file format. Must be valid JSON or YAML: {str(e)}"
                )
        
        # Generate scopes
        from src.api.models.openapi_scopes import ScopeNamingConfig
        
        naming_config = ScopeNamingConfig(namespace=namespace)
        
        result = openapi_scope_generator.generate_scopes(
            spec,
            strategy,
            naming_config,
            category,
            generate_wildcards
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to process file: {str(e)}"
        )


@router.post("/generate/url", response_model=OpenAPIScopeGenerationResponse)
async def generate_scopes_from_url(
    url: str,
    strategy: ScopeGenerationStrategy = ScopeGenerationStrategy.PATH_RESOURCE,
    namespace: str = "api",
    category: str = "api",
    generate_wildcards: bool = True,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:read"]))
):
    """
    Generate scopes from OpenAPI spec URL.
    
    Example URLs:
    - https://petstore3.swagger.io/api/v3/openapi.json
    - https://api.example.com/docs/openapi.json
    - https://api.example.com/swagger.json
    """
    try:
        # Load from URL
        spec = await openapi_scope_generator.load_spec(
            OpenAPISourceType.URL,
            source=url
        )
        
        # Generate scopes
        from src.api.models.openapi_scopes import ScopeNamingConfig
        
        naming_config = ScopeNamingConfig(namespace=namespace)
        
        result = openapi_scope_generator.generate_scopes(
            spec,
            strategy,
            naming_config,
            category,
            generate_wildcards
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to fetch or process OpenAPI spec from URL: {str(e)}"
        )


@router.post("/generate-and-import", response_model=BulkScopesResponse)
async def generate_and_import_scopes(
    request: OpenAPISourceRequest,
    import_to_db: bool = True,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:write"])),
    session: AsyncSession = Depends(get_session)
):
    """
    Generate scopes from OpenAPI spec and optionally import them to database.
    
    This is a convenience endpoint that combines generation and import in one call.
    Set import_to_db=false to only generate without importing.
    """
    try:
        # Load spec
        spec = await openapi_scope_generator.load_spec(
            request.source_type,
            request.source,
            request.spec_data
        )
        
        # Generate scopes
        generation_result = openapi_scope_generator.generate_scopes(
            spec,
            request.strategy,
            request.naming_config,
            request.category,
            request.generate_wildcards
        )
        
        if not import_to_db:
            # Return generation result without importing
            return BulkScopesResponse(
                total_processed=generation_result.total_scopes,
                created=0,
                updated=0,
                skipped=generation_result.total_scopes,
                errors=[],
                scope_names=[s.scope_name for s in generation_result.scopes]
            )
        
        # Convert to bulk format and import
        scopes_data = [
            {
                "scope_name": scope.scope_name,
                "description": scope.description,
                "is_active": scope.is_active
            }
            for scope in generation_result.scopes
        ]
        
        # Perform bulk upsert
        result = await scope_repository.bulk_upsert(session, scopes_data)
        
        # Add warnings as errors if any
        if generation_result.warnings:
            result["errors"].extend(generation_result.warnings)
        
        return BulkScopesResponse(
            total_processed=generation_result.total_scopes,
            created=result["created"],
            updated=result["updated"],
            skipped=result["skipped"],
            errors=result["errors"],
            scope_names=result["scope_names"]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to generate and import scopes: {str(e)}"
        )
