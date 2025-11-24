"""API routes for Sensitive Field management (CRUD).

Sensitive fields support both global (project_id=NULL) and project-specific configurations:
- Global: /sensitive-fields (project_id = NULL in database)
- Project: /projects/{project_id}/sensitive-fields (project_id = X in database)
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_async_session as get_db
from src.database.repositories.sensitive_fields_repository import SensitiveFieldRepository
from src.database.repositories.project_repository import project_repository
from src.api.auth_middleware import PermissionChecker
from src.api.models.sensitive_fields import (
    SensitiveFieldCreate,
    SensitiveFieldUpdate,
    SensitiveFieldResponse,
    SensitiveFieldListResponse,
)
from src.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(tags=["Sensitive Fields"])

READ_SCOPE = "akm:sensitive-fields:read"
CREATE_SCOPE = "akm:sensitive-fields:create"
UPDATE_SCOPE = "akm:sensitive-fields:update"
DELETE_SCOPE = "akm:sensitive-fields:delete"
ANY_SCOPE = "akm:sensitive-fields:*"


def scope_checker(required: str):
    return PermissionChecker([required, ANY_SCOPE])


# Global sensitive fields (project_id = NULL)
@router.get("/sensitive-fields", response_model=SensitiveFieldListResponse, summary="List global sensitive fields")
async def list_sensitive_fields(
    active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(scope_checker(READ_SCOPE)),
):
    repo = SensitiveFieldRepository(db)
    items = await repo.list_fields(project_id=None, active=active)
    return SensitiveFieldListResponse(total=len(items), items=items)


@router.get("/sensitive-fields/{field_id}", response_model=SensitiveFieldResponse, summary="Get global sensitive field by ID")
async def get_sensitive_field(
    field_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(scope_checker(READ_SCOPE)),
):
    repo = SensitiveFieldRepository(db)
    field = await repo.get_by_id(field_id)
    if not field or field.project_id is not None:
        raise HTTPException(status_code=404, detail="Global sensitive field not found")
    return field


@router.post("/sensitive-fields", response_model=SensitiveFieldResponse, summary="Create global sensitive field")
async def create_sensitive_field(
    payload: SensitiveFieldCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(scope_checker(CREATE_SCOPE)),
):
    repo = SensitiveFieldRepository(db)
    existing = await repo.get_by_name(payload.field_name.lower(), project_id=None)
    if existing:
        raise HTTPException(status_code=400, detail="Global field already exists")
    field = await repo.create(
        project_id=None,
        field_name=payload.field_name,
        is_active=payload.is_active,
        strategy=payload.strategy,
        mask_show_start=payload.mask_show_start,
        mask_show_end=payload.mask_show_end,
        mask_char=payload.mask_char,
        replacement=payload.replacement,
    )
    return field


@router.put("/sensitive-fields/{field_id}", response_model=SensitiveFieldResponse, summary="Update global sensitive field")
async def update_sensitive_field(
    field_id: int,
    payload: SensitiveFieldUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(scope_checker(UPDATE_SCOPE)),
):
    repo = SensitiveFieldRepository(db)
    field = await repo.get_by_id(field_id)
    if not field or field.project_id is not None:
        raise HTTPException(status_code=404, detail="Global sensitive field not found")
    
    updated = await repo.update(field_id, **payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Sensitive field not found")
    return updated


@router.delete("/sensitive-fields/{field_id}", summary="Delete global sensitive field", status_code=204)
async def delete_sensitive_field(
    field_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(scope_checker(DELETE_SCOPE)),
):
    repo = SensitiveFieldRepository(db)
    field = await repo.get_by_id(field_id)
    if not field or field.project_id is not None:
        raise HTTPException(status_code=404, detail="Global sensitive field not found")
    
    deleted = await repo.delete(field_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Sensitive field not found")
    return None


# Project-specific sensitive fields
@router.get("/projects/{project_id}/sensitive-fields", response_model=SensitiveFieldListResponse, summary="List project sensitive fields")
async def list_project_sensitive_fields(
    project_id: int,
    active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(scope_checker(READ_SCOPE)),
):
    # Verify project exists
    from src.database.connection import get_session
    async with get_session() as session:
        project = await project_repository.get_by_id(session, project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    
    repo = SensitiveFieldRepository(db)
    items = await repo.list_fields(project_id=project_id, active=active)
    return SensitiveFieldListResponse(total=len(items), items=items)


@router.get("/projects/{project_id}/sensitive-fields/{field_id}", response_model=SensitiveFieldResponse, summary="Get project sensitive field by ID")
async def get_project_sensitive_field(
    project_id: int,
    field_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(scope_checker(READ_SCOPE)),
):
    repo = SensitiveFieldRepository(db)
    field = await repo.get_by_id(field_id)
    if not field or field.project_id != project_id:
        raise HTTPException(status_code=404, detail=f"Sensitive field not found in project {project_id}")
    return field


@router.post("/projects/{project_id}/sensitive-fields", response_model=SensitiveFieldResponse, summary="Create project sensitive field")
async def create_project_sensitive_field(
    project_id: int,
    payload: SensitiveFieldCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(scope_checker(CREATE_SCOPE)),
):
    # Verify project exists
    from src.database.connection import get_session
    async with get_session() as session:
        project = await project_repository.get_by_id(session, project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    
    repo = SensitiveFieldRepository(db)
    existing = await repo.get_by_name(payload.field_name.lower(), project_id=project_id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Field already exists in project {project_id}")
    
    field = await repo.create(
        project_id=project_id,
        field_name=payload.field_name,
        is_active=payload.is_active,
        strategy=payload.strategy,
        mask_show_start=payload.mask_show_start,
        mask_show_end=payload.mask_show_end,
        mask_char=payload.mask_char,
        replacement=payload.replacement,
    )
    return field


@router.put("/projects/{project_id}/sensitive-fields/{field_id}", response_model=SensitiveFieldResponse, summary="Update project sensitive field")
async def update_project_sensitive_field(
    project_id: int,
    field_id: int,
    payload: SensitiveFieldUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(scope_checker(UPDATE_SCOPE)),
):
    repo = SensitiveFieldRepository(db)
    field = await repo.get_by_id(field_id)
    if not field or field.project_id != project_id:
        raise HTTPException(status_code=404, detail=f"Sensitive field not found in project {project_id}")
    
    updated = await repo.update(field_id, **payload.model_dump(exclude_unset=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Sensitive field not found")
    return updated


@router.delete("/projects/{project_id}/sensitive-fields/{field_id}", summary="Delete project sensitive field", status_code=204)
async def delete_project_sensitive_field(
    project_id: int,
    field_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(scope_checker(DELETE_SCOPE)),
):
    repo = SensitiveFieldRepository(db)
    field = await repo.get_by_id(field_id)
    if not field or field.project_id != project_id:
        raise HTTPException(status_code=404, detail=f"Sensitive field not found in project {project_id}")
    
    deleted = await repo.delete(field_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Sensitive field not found")
    return None
