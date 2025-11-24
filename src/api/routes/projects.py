"""
API routes for Project management.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.database.repositories.project_repository import project_repository
from src.database.models import AKMAPIKey
from src.api.auth_middleware import PermissionChecker
from src.api.models import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectWithStats
)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project_data: ProjectCreate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:projects:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Create a new project"""
    # Check if project with same name exists
    existing = await project_repository.get_by_name(session, project_data.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Project with name '{project_data.name}' already exists"
        )
    
    project = await project_repository.create(
        session,
        name=project_data.name,
        prefix=project_data.prefix,
        description=project_data.description
    )
    
    return project


@router.get("", response_model=List[ProjectResponse])
async def list_projects(
    active_only: bool = True,
    skip: int = 0,
    limit: int = 100,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:projects:read"])),
    session: AsyncSession = Depends(get_session)
):
    """List all projects"""
    projects = await project_repository.list_all(
        session,
        active_only=active_only,
        skip=skip,
        limit=limit
    )
    return projects


@router.get("/{project_id}", response_model=ProjectWithStats)
async def get_project(
    project_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:projects:read"])),
    session: AsyncSession = Depends(get_session)
):
    """Get project by ID with statistics"""
    project = await project_repository.get_by_id(session, project_id)
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    # Get key counts
    active_count = await project_repository.get_api_key_count(session, project_id, active_only=True)
    total_count = await project_repository.get_api_key_count(session, project_id, active_only=False)
    
    return ProjectWithStats(
        **project.__dict__,
        active_keys_count=active_count,
        total_keys_count=total_count
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:projects:write"])),
    session: AsyncSession = Depends(get_session)
):
    """Update project"""
    updated = await project_repository.update(
        session,
        project_id,
        name=project_data.name,
        description=project_data.description,
        is_active=project_data.is_active
    )
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    return updated


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    hard_delete: bool = False,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:projects:delete"])),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete project (soft delete by default, cascades to API keys if hard delete).
    
    - **soft delete** (default): Deactivates project
    - **hard delete**: Permanently removes project and all associated API keys
    """
    if hard_delete:
        success = await project_repository.hard_delete(session, project_id)
    else:
        success = await project_repository.delete(session, project_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found"
        )
    
    return None
