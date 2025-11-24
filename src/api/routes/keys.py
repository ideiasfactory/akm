"""
API routes for API Key management.

Keys are now project-scoped following RESTful hierarchy:
- POST   /projects/{project_id}/keys
- GET    /projects/{project_id}/keys
- GET    /projects/{project_id}/keys/{key_id}
- PUT    /projects/{project_id}/keys/{key_id}
- DELETE /projects/{project_id}/keys/{key_id}

Admin route for listing all keys across projects:
- GET /keys (requires admin scope)
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.database.repositories.api_key_repository import api_key_repository
from src.database.repositories.scope_repository import scope_repository
from src.database.repositories.project_repository import project_repository
from src.database.models import AKMAPIKey
from src.api.auth_middleware import PermissionChecker
from src.api.models import (
    APIKeyCreate,
    APIKeyUpdate,
    APIKeyScopesUpdate,
    APIKeyResponse,
    APIKeyCreateResponse,
    APIKeyDetailedResponse,
    ProjectInfo
)

router = APIRouter(tags=["API Keys"])


# Admin route: List all keys across projects
@router.get("/keys", response_model=List[APIKeyDetailedResponse])
async def list_all_api_keys(
    project_id: Optional[int] = None,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:keys:*", "akm:*"])),
    session: AsyncSession = Depends(get_session)
):
    """List all API keys across projects (admin only)"""
    keys = await api_key_repository.list_all(
        session,
        project_id=project_id,
        active_only=active_only,
        skip=skip,
        limit=limit
    )
    
    result = []
    for key in keys:
        key_dict = {k: v for k, v in key.__dict__.items() if k not in ['scopes', 'project']}
        result.append(
            APIKeyDetailedResponse(
                **key_dict,
                scopes=[s.scope.scope_name for s in key.scopes],
                project=ProjectInfo(**key.project.__dict__) if key.project else None
            )
        )
    
    return result


# Project-scoped routes
@router.post("/projects/{project_id}/keys", response_model=APIKeyCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    project_id: int,
    key_data: APIKeyCreate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:keys:write"])),
    session: AsyncSession = Depends(get_session)
):
    """
    Create a new API key with scopes for a project.
    
    Returns the plain API key - **save it securely**, it won't be shown again!
    """
    # Verify project exists
    project = await project_repository.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    # Verify all scopes exist in this project
    for scope_name in key_data.scopes:
        scope = await scope_repository.get_by_project_and_name(session, project_id, scope_name)
        if not scope:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scope '{scope_name}' not found in project {project_id}"
            )
    
    # Create key
    created_key, plain_key = await api_key_repository.create_key(
        session,
        project_id=project_id,
        name=key_data.name,
        scopes=key_data.scopes,
        description=key_data.description,
        expires_at=key_data.expires_at,
        auto_generate=True
    )
    
    # Reload to get relationships
    created_key = await api_key_repository.get_by_id(session, created_key.id)
    
    key_dict = {k: v for k, v in created_key.__dict__.items() if k not in ['scopes', 'project']}
    return APIKeyCreateResponse(
        **key_dict,
        scopes=[s.scope.scope_name for s in created_key.scopes],
        key=plain_key
    )


@router.get("/projects/{project_id}/keys", response_model=List[APIKeyDetailedResponse])
async def list_project_api_keys(
    project_id: int,
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:keys:read"])),
    session: AsyncSession = Depends(get_session)
):
    """List API keys for a specific project"""
    # Verify project exists
    project = await project_repository.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    keys = await api_key_repository.list_all(
        session,
        project_id=project_id,
        active_only=active_only,
        skip=skip,
        limit=limit
    )
    
    result = []
    for key in keys:
        key_dict = {k: v for k, v in key.__dict__.items() if k not in ['scopes', 'project']}
        result.append(
            APIKeyDetailedResponse(
                **key_dict,
                scopes=[s.scope.scope_name for s in key.scopes],
                project=ProjectInfo(**key.project.__dict__) if key.project else None
            )
        )
    
    return result


@router.get("/projects/{project_id}/keys/{key_id}", response_model=APIKeyDetailedResponse)
async def get_api_key(
    project_id: int,
    key_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:keys:read"])),
    session: AsyncSession = Depends(get_session)
):
    """Get API key by ID"""
    key = await api_key_repository.get_by_id(session, key_id, load_scopes=True)
    
    if not key or key.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found in project {project_id}"
        )
    
    key_dict = {k: v for k, v in key.__dict__.items() if k not in ['scopes', 'project']}
    return APIKeyDetailedResponse(
        **key_dict,
        scopes=[s.scope.scope_name for s in key.scopes],
        project=ProjectInfo(**key.project.__dict__) if key.project else None
    )


@router.put("/projects/{project_id}/keys/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    project_id: int,
    key_id: int,
    key_data: APIKeyUpdate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:keys:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Update API key metadata"""
    key = await api_key_repository.get_by_id(session, key_id)
    
    if not key or key.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found in project {project_id}"
        )
    
    updated = await api_key_repository.update_key(
        session,
        key_id,
        name=key_data.name,
        description=key_data.description,
        is_active=key_data.is_active,
        expires_at=key_data.expires_at
    )
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found"
        )
    
    # Reload with scopes
    updated = await api_key_repository.get_by_id(session, key_id)
    
    key_dict = {k: v for k, v in updated.__dict__.items() if k not in ['scopes', 'project']}
    return APIKeyDetailedResponse(
        **key_dict,
        scopes=[s.scope.scope_name for s in updated.scopes]
    )


@router.put("/projects/{project_id}/keys/{key_id}/scopes", response_model=APIKeyResponse)
async def update_api_key_scopes(
    project_id: int,
    key_id: int,
    scope_data: APIKeyScopesUpdate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:keys:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Replace all scopes for an API key"""
    key = await api_key_repository.get_by_id(session, key_id)
    
    if not key or key.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found in project {project_id}"
        )
    
    # Verify all scopes exist in this project
    for scope_name in scope_data.scopes:
        scope = await scope_repository.get_by_project_and_name(session, project_id, scope_name)
        if not scope:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scope '{scope_name}' not found in project {project_id}"
            )
    
    success = await api_key_repository.set_scopes(session, key_id, scope_data.scopes)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found"
        )
    
    # Reload with new scopes
    updated = await api_key_repository.get_by_id(session, key_id)
    
    key_dict = {k: v for k, v in updated.__dict__.items() if k not in ['scopes', 'project']}
    return APIKeyResponse(
        **key_dict,
        scopes=[s.scope.scope_name for s in updated.scopes]
    )


@router.delete("/projects/{project_id}/keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    project_id: int,
    key_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:keys:delete"])),
    session: AsyncSession = Depends(get_session)
):
    """Permanently delete an API key (cascades to scopes and config)"""
    key = await api_key_repository.get_by_id(session, key_id)
    
    if not key or key.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found in project {project_id}"
        )
    
    success = await api_key_repository.delete_key(session, key_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found"
        )
    
    return None


@router.post("/projects/{project_id}/keys/{key_id}/revoke", response_model=APIKeyResponse)
async def revoke_api_key(
    project_id: int,
    key_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:keys:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Revoke (deactivate) an API key without deleting it"""
    key = await api_key_repository.get_by_id(session, key_id)
    
    if not key or key.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found in project {project_id}"
        )
    
    success = await api_key_repository.revoke_key(session, key_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"API key {key_id} not found"
        )
    
    # Return updated key
    updated = await api_key_repository.get_by_id(session, key_id)
    
    key_dict = {k: v for k, v in updated.__dict__.items() if k not in ['scopes', 'project']}
    return APIKeyResponse(
        **key_dict,
        scopes=[s.scope.scope_name for s in updated.scopes]
    )

