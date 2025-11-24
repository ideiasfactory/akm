"""
API routes for Scope management.

Scopes are now project-scoped following RESTful hierarchy:
- POST   /projects/{project_id}/scopes
- GET    /projects/{project_id}/scopes
- GET    /projects/{project_id}/scopes/{scope_id}
- PUT    /projects/{project_id}/scopes/{scope_id}
- DELETE /projects/{project_id}/scopes/{scope_id}
"""

from typing import List
from pathlib import Path
import json
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.database.repositories.scope_repository import scope_repository
from src.database.repositories.project_repository import project_repository
from src.database.models import AKMAPIKey
from src.api.auth_middleware import PermissionChecker
from src.api.models import (
    ScopeCreate,
    ScopeUpdate,
    ScopeResponse,
    BulkScopesRequest,
    BulkScopesResponse,
)

router = APIRouter(tags=["Scopes"])


@router.post("/projects/{project_id}/scopes", response_model=ScopeResponse, status_code=status.HTTP_201_CREATED)
async def create_scope(
    project_id: int,
    scope_data: ScopeCreate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Create a new scope for a project"""
    # Verify project exists
    project = await project_repository.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    # Check if scope exists in this project
    existing = await scope_repository.get_by_project_and_name(session, project_id, scope_data.scope_name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Scope '{scope_data.scope_name}' already exists in project {project_id}"
        )
    
    scope = await scope_repository.create(
        session,
        project_id=project_id,
        scope_name=scope_data.scope_name,
        description=scope_data.description
    )
    
    return scope


@router.get("/projects/{project_id}/scopes", response_model=List[ScopeResponse])
async def list_scopes(
    project_id: int,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:read"])),
    session: AsyncSession = Depends(get_session)
):
    """List all scopes for a project"""
    # Verify project exists
    project = await project_repository.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    scopes = await scope_repository.list_by_project(
        session,
        project_id=project_id,
        active_only=active_only,
        skip=skip,
        limit=limit
    )
    return scopes


@router.get("/projects/{project_id}/scopes/{scope_id}", response_model=ScopeResponse)
async def get_scope(
    project_id: int,
    scope_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:read"])),
    session: AsyncSession = Depends(get_session)
):
    """Get scope by ID"""
    scope = await scope_repository.get_by_id(session, scope_id)
    
    if not scope or scope.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scope {scope_id} not found in project {project_id}"
        )
    
    return scope


@router.put("/projects/{project_id}/scopes/{scope_id}", response_model=ScopeResponse)
async def update_scope(
    project_id: int,
    scope_id: int,
    scope_data: ScopeUpdate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Update scope"""
    scope = await scope_repository.get_by_id(session, scope_id)
    
    if not scope or scope.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scope {scope_id} not found in project {project_id}"
        )
    
    updated = await scope_repository.update_by_id(
        session,
        scope_id,
        description=scope_data.description,
        is_active=scope_data.is_active
    )
    
    return updated


@router.delete("/projects/{project_id}/scopes/{scope_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scope(
    project_id: int,
    scope_id: int,
    hard_delete: bool = False,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:delete"])),
    session: AsyncSession = Depends(get_session)
):
    """Delete scope (soft delete by default)"""
    scope = await scope_repository.get_by_id(session, scope_id)
    
    if not scope or scope.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scope {scope_id} not found in project {project_id}"
        )
    
    if hard_delete:
        success = await scope_repository.hard_delete_by_id(session, scope_id)
    else:
        success = await scope_repository.delete_by_id(session, scope_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scope {scope_id} not found"
        )
    
    return None


@router.post("/projects/{project_id}/scopes/bulk", response_model=BulkScopesResponse, status_code=status.HTTP_200_OK)
async def bulk_upsert_scopes(
    project_id: int,
    request: BulkScopesRequest,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Bulk upsert scopes from JSON data for a project
    
    Creates new scopes or updates existing ones based on scope_name.
    Validates against JSON schema before processing.
    """
    # Verify project exists
    project = await project_repository.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    # Convert Pydantic models to dicts for repository
    scopes_data = [scope.model_dump() for scope in request.scopes]
    
    # Perform bulk upsert
    result = await scope_repository.bulk_upsert(session, project_id, scopes_data)
    
    # Build response
    return BulkScopesResponse(
        total_processed=len(request.scopes),
        created=result["created"],
        updated=result["updated"],
        skipped=result["skipped"],
        errors=result["errors"],
        scope_names=result["scope_names"]
    )


@router.post("/projects/{project_id}/scopes/bulk/file", response_model=BulkScopesResponse, status_code=status.HTTP_200_OK)
async def bulk_upsert_scopes_from_file(
    project_id: int,
    file: UploadFile = File(..., description="JSON file with scopes data"),
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Bulk upsert scopes from uploaded JSON file for a project
    
    Uploads a JSON file with scopes structure and validates against schema.
    """
    # Verify project exists
    project = await project_repository.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
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
    result = await scope_repository.bulk_upsert(session, project_id, scopes_data)
    
    # Build response
    return BulkScopesResponse(
        total_processed=len(request.scopes),
        created=result["created"],
        updated=result["updated"],
        skipped=result["skipped"],
        errors=result["errors"],
        scope_names=result["scope_names"]
    )


@router.get("/projects/{project_id}/scopes/export/json", response_model=BulkScopesRequest)
async def export_scopes_json(
    project_id: int,
    active_only: bool = True,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:scopes:read"])),
    session: AsyncSession = Depends(get_session)
):
    """Export all scopes to JSON format compatible with bulk import"""
    # Verify project exists
    project = await project_repository.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    scopes = await scope_repository.list_by_project(
        session,
        project_id=project_id,
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

