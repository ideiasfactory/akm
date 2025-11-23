"""Repository for managing sensitive field configurations."""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from src.database.models import AKMSensitiveField
from src.logging_config import get_logger

logger = get_logger(__name__)


class SensitiveFieldRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_fields(self, active: Optional[bool] = None) -> List[AKMSensitiveField]:
        stmt = select(AKMSensitiveField)
        if active is not None:
            stmt = stmt.where(AKMSensitiveField.is_active == active)
        result = await self.db.execute(stmt.order_by(AKMSensitiveField.field_name.asc()))
        return list(result.scalars().all())

    async def get_by_id(self, field_id: int) -> Optional[AKMSensitiveField]:
        result = await self.db.execute(select(AKMSensitiveField).where(AKMSensitiveField.id == field_id))
        return result.scalar_one_or_none()

    async def get_by_name(self, field_name: str) -> Optional[AKMSensitiveField]:
        result = await self.db.execute(select(AKMSensitiveField).where(AKMSensitiveField.field_name == field_name))
        return result.scalar_one_or_none()

    async def create(
        self,
        field_name: str,
        is_active: bool = True,
        strategy: Optional[str] = None,
        mask_show_start: Optional[int] = None,
        mask_show_end: Optional[int] = None,
        mask_char: Optional[str] = None,
        replacement: Optional[str] = None,
    ) -> AKMSensitiveField:
        field = AKMSensitiveField(
            field_name=field_name.lower(),
            is_active=is_active,
            strategy=strategy,
            mask_show_start=mask_show_start,
            mask_show_end=mask_show_end,
            mask_char=mask_char,
            replacement=replacement,
        )
        self.db.add(field)
        try:
            await self.db.flush()
        except SQLAlchemyError as e:
            logger.error("Failed to create sensitive field: %s", e)
            raise
        return field

    async def update(
        self,
        field_id: int,
        **updates,
    ) -> Optional[AKMSensitiveField]:
        field = await self.get_by_id(field_id)
        if not field:
            return None
        for key, value in updates.items():
            if hasattr(field, key) and value is not None:
                setattr(field, key, value)
        try:
            await self.db.flush()
        except SQLAlchemyError as e:
            logger.error("Failed to update sensitive field: %s", e)
            raise
        return field

    async def delete(self, field_id: int) -> bool:
        field = await self.get_by_id(field_id)
        if not field:
            return False
        await self.db.delete(field)
        try:
            await self.db.flush()
        except SQLAlchemyError as e:
            logger.error("Failed to delete sensitive field: %s", e)
            raise
        return True
