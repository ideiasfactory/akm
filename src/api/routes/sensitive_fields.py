"""API routes for Sensitive Field management (CRUD)."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_async_session as get_db
from src.database.repositories.sensitive_fields_repository import SensitiveFieldRepository
from src.api.auth_middleware import PermissionChecker
from src.api.models.sensitive_fields import (
    SensitiveFieldCreate,
    SensitiveFieldUpdate,
    SensitiveFieldResponse,
    SensitiveFieldListResponse,
)
from src.logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/sensitive-fields", tags=["Sensitive Fields"])

READ_SCOPE = "akm:sensitive-fields:read"
CREATE_SCOPE = "akm:sensitive-fields:create"
UPDATE_SCOPE = "akm:sensitive-fields:update"
DELETE_SCOPE = "akm:sensitive-fields:delete"
ANY_SCOPE = "akm:sensitive-fields:*"


def scope_checker(required: str):
    return PermissionChecker([required, ANY_SCOPE])


@router.get("/", response_model=SensitiveFieldListResponse, summary="List sensitive fields")
async def list_sensitive_fields(
    active: Optional[bool] = Query(None, description="Filter by active status"),
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(scope_checker(READ_SCOPE)),
):
    repo = SensitiveFieldRepository(db)
    items = await repo.list_fields(active=active)
    return SensitiveFieldListResponse(total=len(items), items=items)


@router.get("/{field_id}", response_model=SensitiveFieldResponse, summary="Get sensitive field by ID")
async def get_sensitive_field(
    field_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(scope_checker(READ_SCOPE)),
):
    repo = SensitiveFieldRepository(db)
    field = await repo.get_by_id(field_id)
    if not field:
        raise HTTPException(status_code=404, detail="Sensitive field not found")
    return field


@router.post("/", response_model=SensitiveFieldResponse, summary="Create sensitive field")
async def create_sensitive_field(
    payload: SensitiveFieldCreate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(scope_checker(CREATE_SCOPE)),
):
    repo = SensitiveFieldRepository(db)
    existing = await repo.get_by_name(payload.field_name.lower())
    if existing:
        raise HTTPException(status_code=400, detail="Field already exists")
    field = await repo.create(
        field_name=payload.field_name,
        is_active=payload.is_active,
        strategy=payload.strategy,
        mask_show_start=payload.mask_show_start,
        mask_show_end=payload.mask_show_end,
        mask_char=payload.mask_char,
        replacement=payload.replacement,
    )
    return field


@router.put("/{field_id}", response_model=SensitiveFieldResponse, summary="Update sensitive field")
async def update_sensitive_field(
    field_id: int,
    payload: SensitiveFieldUpdate,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(scope_checker(UPDATE_SCOPE)),
):
    repo = SensitiveFieldRepository(db)
    field = await repo.update(field_id, **payload.model_dump(exclude_unset=True))
    if not field:
        raise HTTPException(status_code=404, detail="Sensitive field not found")
    return field


@router.delete("/{field_id}", summary="Delete sensitive field", status_code=204)
async def delete_sensitive_field(
    field_id: int,
    db: AsyncSession = Depends(get_db),
    _: dict = Depends(scope_checker(DELETE_SCOPE)),
):
    repo = SensitiveFieldRepository(db)
    deleted = await repo.delete(field_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Sensitive field not found")
    return None
