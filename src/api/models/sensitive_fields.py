"""Pydantic models for Sensitive Field management."""
from typing import Optional, List
from pydantic import BaseModel, Field


class SensitiveFieldBase(BaseModel):
    field_name: str = Field(..., description="Name of the sensitive field (case-insensitive)")
    is_active: bool = Field(True, description="Whether the field is active for sanitization")
    strategy: Optional[str] = Field(None, description="Override strategy: redact | mask")
    mask_show_start: Optional[int] = Field(None, ge=0, description="Override: number of leading chars to show when masking")
    mask_show_end: Optional[int] = Field(None, ge=0, description="Override: number of trailing chars to show when masking")
    mask_char: Optional[str] = Field(None, min_length=1, max_length=1, description="Override: masking character")
    replacement: Optional[str] = Field(None, description="Override replacement string for redact strategy")


class SensitiveFieldCreate(SensitiveFieldBase):
    pass


class SensitiveFieldUpdate(BaseModel):
    is_active: Optional[bool] = None
    strategy: Optional[str] = Field(None, description="Override strategy: redact | mask")
    mask_show_start: Optional[int] = Field(None, ge=0)
    mask_show_end: Optional[int] = Field(None, ge=0)
    mask_char: Optional[str] = Field(None, min_length=1, max_length=1)
    replacement: Optional[str] = None


class SensitiveFieldResponse(SensitiveFieldBase):
    id: int

    class Config:
        from_attributes = True


class SensitiveFieldListResponse(BaseModel):
    total: int
    items: List[SensitiveFieldResponse]
