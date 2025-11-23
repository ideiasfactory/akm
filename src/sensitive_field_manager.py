"""Manager for merging sensitive field configuration from file, DB and global settings."""
from __future__ import annotations
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timedelta
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database.models import AKMSensitiveField
from src.config import settings
from src.logging_config import get_logger

logger = get_logger(__name__)

CONFIG_FILE = Path("data/sensitive_fields.json")
CACHE_TTL_SECONDS = 300


class SensitiveFieldManager:
    def __init__(self, db: AsyncSession):
        self.db = db
        self._fields_config: Dict[str, Dict[str, Any]] = {}
        self._last_loaded: Optional[datetime] = None

    async def _load_from_db(self) -> Dict[str, Dict[str, Any]]:
        result = await self.db.execute(select(AKMSensitiveField).where(AKMSensitiveField.is_active == True))
        fields: List[AKMSensitiveField] = list(result.scalars().all())
        db_map: Dict[str, Dict[str, Any]] = {}
        for f in fields:
            db_map[f.field_name.lower()] = {
                "strategy": f.strategy,
                "mask_show_start": f.mask_show_start,
                "mask_show_end": f.mask_show_end,
                "mask_char": f.mask_char,
                "replacement": f.replacement,
            }
        return db_map

    def _load_from_file(self) -> Dict[str, Dict[str, Any]]:
        if not CONFIG_FILE.exists():
            return {}
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Failed to read sensitive fields config file: %s", e)
            return {}
        file_map: Dict[str, Dict[str, Any]] = {}
        for item in data.get("fields", []):
            if isinstance(item, dict):
                name = str(item.get("field_name", "")).strip().lower()
                if name:
                    file_map[name] = {
                        "strategy": item.get("strategy"),
                        "mask_show_start": item.get("mask_show_start"),
                        "mask_show_end": item.get("mask_show_end"),
                        "mask_char": item.get("mask_char"),
                        "replacement": item.get("replacement"),
                    }
            elif isinstance(item, str):
                file_map[item.lower()] = {}
        return file_map

    async def load(self, force: bool = False) -> None:
        if not force and self._last_loaded and datetime.utcnow() - self._last_loaded < timedelta(seconds=CACHE_TTL_SECONDS):
            return
        file_map = self._load_from_file()
        db_map = await self._load_from_db()
        merged = {**file_map, **db_map}  # DB overrides file
        self._fields_config = merged
        self._last_loaded = datetime.utcnow()
        logger.debug("Sensitive fields loaded: %d entries", len(self._fields_config))

    async def get_fields(self) -> Dict[str, Dict[str, Any]]:
        await self.load()
        return self._fields_config

    async def is_sensitive(self, key: str) -> bool:
        key_lower = key.lower()
        fields = await self.get_fields()
        return key_lower in fields or any(k in key_lower for k in fields.keys())

    async def get_field_config(self, key: str) -> Dict[str, Any]:
        fields = await self.get_fields()
        return fields.get(key.lower(), {})

    def get_global_strategy(self) -> Dict[str, Any]:
        return {
            "strategy": settings.sanitization_strategy,
            "replacement": settings.sanitization_replacement,
            "mask_show_start": settings.sanitization_mask_show_start,
            "mask_show_end": settings.sanitization_mask_show_end,
            "mask_char": settings.sanitization_mask_char,
        }
