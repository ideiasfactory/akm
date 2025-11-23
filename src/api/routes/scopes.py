"""
API routes for Scope management.
"""

from typing import List
from pathlib import Path
import json
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.database.repositories.scope_repository import scope_repository
from src.database.models import AKMAPIKey
from src.api.auth_middleware import PermissionChecker
from src.api.models import (
    ScopeCreate,
    ScopeUpdate,
    ScopeResponse,
    BulkScopesRequest,
    BulkScopesResponse,
)

router = APIRouter(prefix="/scopes", tags=["Scopes"])


@router.post("", response_model=ScopeResponse, status_code=status.HTTP_201_CREATED)
async def create_scope(
    scope_data: ScopeCreate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Create a new scope"""
    # Check if scope exists
    existing = await scope_repository.get_by_name(session, scope_data.scope_name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Scope '{scope_data.scope_name}' already exists"
        )
    
    scope = await scope_repository.create(
        session,
        scope_name=scope_data.scope_name,
        description=scope_data.description
    )
    
    return scope


@router.get("", response_model=List[ScopeResponse])
async def list_scopes(
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:read"])),
    session: AsyncSession = Depends(get_session)
):
    """List all scopes"""
    scopes = await scope_repository.list_all(
        session,
        active_only=active_only,
        skip=skip,
        limit=limit
    )
    return scopes


@router.get("/{scope_name}", response_model=ScopeResponse)
async def get_scope(
    scope_name: str,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:read"])),
    session: AsyncSession = Depends(get_session)
):
    """Get scope by name"""
    scope = await scope_repository.get_by_name(session, scope_name)
    
    if not scope:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scope '{scope_name}' not found"
        )
    
    return scope


@router.put("/{scope_name}", response_model=ScopeResponse)
async def update_scope(
    scope_name: str,
    scope_data: ScopeUpdate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Update scope"""
    updated = await scope_repository.update(
        session,
        scope_name,
        description=scope_data.description,
        is_active=scope_data.is_active
    )
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scope '{scope_name}' not found"
        )
    
    return updated


@router.delete("/{scope_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scope(
    scope_name: str,
    hard_delete: bool = False,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:delete"])),
    session: AsyncSession = Depends(get_session)
):
    """Delete scope (soft delete by default)"""
    if hard_delete:
        success = await scope_repository.hard_delete(session, scope_name)
    else:
        success = await scope_repository.delete(session, scope_name)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scope '{scope_name}' not found"
        )
    
    return None


@router.post("/bulk", response_model=BulkScopesResponse, status_code=status.HTTP_200_OK)
async def bulk_upsert_scopes(
    request: BulkScopesRequest,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Bulk upsert scopes from JSON data
    
    Creates new scopes or updates existing ones based on scope_name.
    Validates against JSON schema before processing.
    """
    # Convert Pydantic models to dicts for repository
    scopes_data = [scope.model_dump() for scope in request.scopes]
    
    # Perform bulk upsert
    result = await scope_repository.bulk_upsert(session, scopes_data)
    
    # Build response
    return BulkScopesResponse(
        total_processed=len(request.scopes),
        created=result["created"],
        updated=result["updated"],
        skipped=result["skipped"],
        errors=result["errors"],
        scope_names=result["scope_names"]
    )


@router.post("/bulk/file", response_model=BulkScopesResponse, status_code=status.HTTP_200_OK)
async def bulk_upsert_scopes_from_file(
    file: UploadFile = File(..., description="JSON file with scopes data"),
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Bulk upsert scopes from uploaded JSON file
    
    Uploads a JSON file with scopes structure and validates against schema.
    """
    # Validate file extension
    if not file.filename.endswith('.json'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a JSON file (.json extension)"
        )
    
    try:
        # Read file content
        content = await file.read()
        data = json.loads(content)
        
        # Validate against Pydantic model (which validates against schema rules)
        request = BulkScopesRequest(**data)
        
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    
    # Convert Pydantic models to dicts for repository
    scopes_data = [scope.model_dump() for scope in request.scopes]
    
    # Perform bulk upsert
    result = await scope_repository.bulk_upsert(session, scopes_data)
    
    # Build response
    return BulkScopesResponse(
        total_processed=len(request.scopes),
        created=result["created"],
        updated=result["updated"],
        skipped=result["skipped"],
        errors=result["errors"],
        scope_names=result["scope_names"]
    )


@router.get("/export/json", response_model=BulkScopesRequest)
async def export_scopes_json(
    active_only: bool = True,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:read"])),
    session: AsyncSession = Depends(get_session)
):
    """Export all scopes to JSON format compatible with bulk import"""
    scopes = await scope_repository.list_all(
        session,
        active_only=active_only,
        skip=0,
        limit=1000  # High limit to get all scopes
    )
    
    # Convert to bulk format
    scope_items = []
    for scope in scopes:
        # Infer category from scope name
        parts = scope.scope_name.split(':')
        category = parts[1] if len(parts) > 1 else 'system'
        
        scope_items.append({
            "scope_name": scope.scope_name,
            "description": scope.description or "",
            "category": category,
            "is_active": scope.is_active
        })
    
    return BulkScopesRequest(
        version="1.0.0",
        scopes=scope_items
    )
