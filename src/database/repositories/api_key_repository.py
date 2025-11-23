"""
API Key Repository for database operations.

Handles CRUD operations for API keys with project association,
scope management, and configuration.
"""

from datetime import datetime
from typing import Optional, List
import hashlib
import secrets

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import (
    AKMAPIKey,
    AKMAPIKeyScope,
    AKMAPIKeyConfig,
    AKMProject,
    AKMScope
)


class APIKeyRepository:
    """Repository for API Key operations with scope and project support"""

    @staticmethod
    def hash_key(key: str) -> str:
        """
        Hash an API key using SHA-256.

        Args:
            key: Plain text API key

        Returns:
            Hashed key (hex digest)
        """
        return hashlib.sha256(key.encode()).hexdigest()
    
    @staticmethod
    def generate_key(prefix: str = "akm", length: int = 32) -> str:
        """
        Generate a secure random API key.
        
        Args:
            prefix: Key prefix (default: "akm")
            length: Length of random part
            
        Returns:
            Generated API key (e.g., "akm_abc123...")
        """
        random_part = secrets.token_urlsafe(length)
        return f"{prefix}_{random_part}"

    async def validate_key(
        self,
        session: AsyncSession,
        key: str
    ) -> Optional[AKMAPIKey]:
        """
        Validate an API key and return the associated record with scopes if valid.

        Args:
            session: Async database session
            key: Plain text API key to validate

        Returns:
            APIKey record with scopes loaded if valid, None otherwise
        """
        key_hash = self.hash_key(key)

        stmt = select(AKMAPIKey).where(
            and_(
                AKMAPIKey.key_hash == key_hash,
                AKMAPIKey.is_active.is_(True)
            )
        ).options(
            selectinload(AKMAPIKey.scopes).selectinload(AKMAPIKeyScope.scope),
            selectinload(AKMAPIKey.config),
            selectinload(AKMAPIKey.project)
        )

        result = await session.execute(stmt)
        api_key_record = result.scalar_one_or_none()

        if not api_key_record:
            return None

        # Check expiration
        if api_key_record.is_expired():
            return None

        # Update last used timestamp and increment counter
        api_key_record.last_used_at = datetime.utcnow()
        api_key_record.request_count += 1
        
        await session.commit()
        await session.refresh(api_key_record)

        return api_key_record

    async def create_key(
        self,
        session: AsyncSession,
        project_id: int,
        name: str,
        scopes: List[str],
        description: Optional[str] = None,
        expires_at: Optional[datetime] = None,
        auto_generate: bool = True
    ) -> tuple[AKMAPIKey, Optional[str]]:
        """
        Create a new API key with scopes.

        Args:
            session: Async database session
            project_id: Project ID to associate key with
            name: Friendly name for the key
            scopes: List of scope names to assign
            description: Optional description
            expires_at: Optional expiration datetime
            auto_generate: If True, generates a random key

        Returns:
            Tuple of (APIKey record, plain key if auto_generated else None)
        """
        # Generate or use provided key
        plain_key = self.generate_key() if auto_generate else None
        key_hash = self.hash_key(plain_key) if plain_key else None
        
        if not key_hash:
            raise ValueError("Key hash is required")

        api_key = AKMAPIKey(
            project_id=project_id,
            key_hash=key_hash,
            name=name,
            description=description,
            expires_at=expires_at,
            is_active=True
        )

        session.add(api_key)
        await session.flush()

        # Add scopes (resolve scope names to IDs)
        for scope_name in scopes:
            # Get scope by name
            scope_stmt = select(AKMScope).where(AKMScope.scope_name == scope_name)
            scope_result = await session.execute(scope_stmt)
            scope = scope_result.scalar_one_or_none()
            
            if not scope:
                raise ValueError(f"Scope '{scope_name}' not found")
            
            key_scope = AKMAPIKeyScope(
                api_key_id=api_key.id,
                scope_id=scope.id
            )
            session.add(key_scope)

        # Create default config
        config = AKMAPIKeyConfig(
            api_key_id=api_key.id,
            rate_limit_enabled=False
        )
        session.add(config)

        await session.commit()
        await session.refresh(api_key)

        return api_key, plain_key

    async def get_by_id(
        self,
        session: AsyncSession,
        key_id: int,
        load_scopes: bool = True
    ) -> Optional[AKMAPIKey]:
        """Get API key by ID"""
        stmt = select(AKMAPIKey).where(AKMAPIKey.id == key_id)
        
        if load_scopes:
            stmt = stmt.options(
                selectinload(AKMAPIKey.scopes),
                selectinload(AKMAPIKey.config),
                selectinload(AKMAPIKey.project)
            )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        session: AsyncSession,
        name: str,
        project_id: Optional[int] = None
    ) -> Optional[AKMAPIKey]:
        """Get API key by name (optionally filtered by project)"""
        stmt = select(AKMAPIKey).where(AKMAPIKey.name == name)
        
        if project_id:
            stmt = stmt.where(AKMAPIKey.project_id == project_id)
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_all(
        self,
        session: AsyncSession,
        project_id: Optional[int] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[AKMAPIKey]:
        """List API keys with optional filtering"""
        stmt = select(AKMAPIKey)

        if project_id:
            stmt = stmt.where(AKMAPIKey.project_id == project_id)
        
        if active_only:
            stmt = stmt.where(AKMAPIKey.is_active.is_(True))

        stmt = stmt.options(
            selectinload(AKMAPIKey.scopes),
            selectinload(AKMAPIKey.project)
        ).offset(skip).limit(limit).order_by(AKMAPIKey.created_at.desc())

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def update_key(
        self,
        session: AsyncSession,
        key_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        expires_at: Optional[datetime] = None
    ) -> Optional[AKMAPIKey]:
        """Update API key metadata"""
        api_key = await self.get_by_id(session, key_id, load_scopes=False)

        if not api_key:
            return None

        if name is not None:
            api_key.name = name
        if description is not None:
            api_key.description = description
        if is_active is not None:
            api_key.is_active = is_active
        if expires_at is not None:
            api_key.expires_at = expires_at

        await session.commit()
        await session.refresh(api_key)

        return api_key

    async def add_scopes(
        self,
        session: AsyncSession,
        key_id: int,
        scope_names: List[str]
    ) -> bool:
        """Add scopes to an API key"""
        api_key = await self.get_by_id(session, key_id)
        
        if not api_key:
            return False
        
        # Get existing scopes (through relationship)
        existing_scopes = {scope.scope.scope_name for scope in api_key.scopes}
        
        # Add new scopes
        for scope_name in scope_names:
            if scope_name not in existing_scopes:
                # Get scope by name to get scope_id
                scope_stmt = select(AKMScope).where(AKMScope.scope_name == scope_name)
                scope_result = await session.execute(scope_stmt)
                scope = scope_result.scalar_one_or_none()
                
                if not scope:
                    raise ValueError(f"Scope '{scope_name}' not found")
                
                key_scope = AKMAPIKeyScope(
                    api_key_id=key_id,
                    scope_id=scope.id
                )
                session.add(key_scope)
        
        await session.commit()
        return True

    async def remove_scopes(
        self,
        session: AsyncSession,
        key_id: int,
        scope_names: List[str]
    ) -> bool:
        """Remove scopes from an API key"""
        # Get scope IDs from names
        scope_stmt = select(AKMScope).where(AKMScope.scope_name.in_(scope_names))
        scope_result = await session.execute(scope_stmt)
        scopes = scope_result.scalars().all()
        scope_ids = [scope.id for scope in scopes]
        
        # Delete API key scopes by scope_id
        stmt = select(AKMAPIKeyScope).where(
            and_(
                AKMAPIKeyScope.api_key_id == key_id,
                AKMAPIKeyScope.scope_id.in_(scope_ids)
            )
        )
        result = await session.execute(stmt)
        scopes_to_remove = result.scalars().all()
        
        for scope in scopes_to_remove:
            await session.delete(scope)
        
        await session.commit()
        return True

    async def set_scopes(
        self,
        session: AsyncSession,
        key_id: int,
        scope_names: List[str]
    ) -> bool:
        """Replace all scopes for an API key"""
        # Remove all existing scopes
        stmt = select(AKMAPIKeyScope).where(AKMAPIKeyScope.api_key_id == key_id)
        result = await session.execute(stmt)
        existing_scopes = result.scalars().all()
        
        for scope in existing_scopes:
            await session.delete(scope)
        
        # Add new scopes
        for scope_name in scope_names:
            key_scope = AKMAPIKeyScope(
                api_key_id=key_id,
                scope_name=scope_name
            )
            session.add(key_scope)
        
        await session.commit()
        return True

    async def revoke_key(
        self,
        session: AsyncSession,
        key_id: int
    ) -> bool:
        """Revoke (deactivate) an API key"""
        api_key = await self.get_by_id(session, key_id, load_scopes=False)

        if not api_key:
            return False

        api_key.is_active = False
        await session.commit()

        return True

    async def delete_key(
        self,
        session: AsyncSession,
        key_id: int
    ) -> bool:
        """Permanently delete an API key (cascades to scopes and config)"""
        api_key = await self.get_by_id(session, key_id, load_scopes=False)

        if not api_key:
            return False

        await session.delete(api_key)
        await session.commit()

        return True
    
    async def get_key_with_config(
        self,
        session: AsyncSession,
        key_id: int
    ) -> Optional[AKMAPIKey]:
        """Get API key with configuration loaded"""
        stmt = select(AKMAPIKey).where(
            AKMAPIKey.id == key_id
        ).options(
            selectinload(AKMAPIKey.config)
        )
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


# Singleton instance
api_key_repository = APIKeyRepository()
