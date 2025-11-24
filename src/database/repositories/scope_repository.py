"""
Repository for Scope operations.

Handles CRUD operations for permission scopes in the API key management system.
"""

from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import AKMScope


class ScopeRepository:
    """Repository for scope management operations"""

    async def delete_all_by_project(
        self,
        session: AsyncSession,
        project_id: int
    ) -> int:
        """Delete all scopes for a given project (hard delete). Returns number deleted."""
        from sqlalchemy import delete
        stmt = delete(AKMScope).where(AKMScope.project_id == project_id)
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount

    async def create(
        self,
        session: AsyncSession,
        scope_name: str,
        project_id: int,
        description: Optional[str] = None
    ) -> AKMScope:
        """Create a new scope"""
        scope = AKMScope(
            project_id=project_id,
            scope_name=scope_name,
            description=description,
            is_active=True
        )
        
        session.add(scope)
        await session.commit()
        await session.refresh(scope)
        
        return scope
    
    async def get_by_name(
        self,
        session: AsyncSession,
        scope_name: str
    ) -> Optional[AKMScope]:
        """Get scope by name (first match across all projects)"""
        stmt = select(AKMScope).where(AKMScope.scope_name == scope_name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_id(
        self,
        session: AsyncSession,
        scope_id: int
    ) -> Optional[AKMScope]:
        """Get scope by ID"""
        stmt = select(AKMScope).where(AKMScope.id == scope_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_project_and_name(
        self,
        session: AsyncSession,
        project_id: int,
        scope_name: str
    ) -> Optional[AKMScope]:
        """Get scope by project_id and name"""
        stmt = select(AKMScope).where(
            AKMScope.project_id == project_id,
            AKMScope.scope_name == scope_name
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_by_project(
        self,
        session: AsyncSession,
        project_id: int,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[AKMScope]:
        """List scopes for a specific project with pagination"""
        stmt = select(AKMScope).where(AKMScope.project_id == project_id)
        
        if active_only:
            stmt = stmt.where(AKMScope.is_active == True)
        
        stmt = stmt.offset(skip).limit(limit).order_by(AKMScope.scope_name)
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def list_all(
        self,
        session: AsyncSession,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[AKMScope]:
        """List all scopes with pagination"""
        stmt = select(AKMScope)
        
        if active_only:
            stmt = stmt.where(AKMScope.is_active == True)
        
        stmt = stmt.offset(skip).limit(limit).order_by(AKMScope.scope_name)
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def update(
        self,
        session: AsyncSession,
        scope_name: str,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[AKMScope]:
        """Update scope by name (first match)"""
        scope = await self.get_by_name(session, scope_name)
        
        if not scope:
            return None
        
        if description is not None:
            setattr(scope, "description", description)
        if is_active is not None:
            setattr(scope, "is_active", is_active)
        
        await session.commit()
        await session.refresh(scope)
        
        return scope
    
    async def update_by_id(
        self,
        session: AsyncSession,
        scope_id: int,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[AKMScope]:
        """Update scope by ID"""
        scope = await self.get_by_id(session, scope_id)
        
        if not scope:
            return None
        
        if description is not None:
            setattr(scope, "description", description)
        if is_active is not None:
            setattr(scope, "is_active", is_active)
        
        await session.commit()
        await session.refresh(scope)
        
        return scope
    
    async def delete(
        self,
        session: AsyncSession,
        scope_name: str
    ) -> bool:
        """Delete scope by name (soft delete - deactivate, first match)"""
        scope = await self.get_by_name(session, scope_name)
        
        if not scope:
            return False
        
        setattr(scope, "is_active", False)
        await session.commit()
        return True
    
    async def delete_by_id(
        self,
        session: AsyncSession,
        scope_id: int
    ) -> bool:
        """Delete scope by ID (soft delete - deactivate)"""
        scope = await self.get_by_id(session, scope_id)
        
        if not scope:
            return False
        
        setattr(scope, "is_active", False)
        await session.commit()
        return True
    
    async def hard_delete(
        self,
        session: AsyncSession,
        scope_name: str
    ) -> bool:
        """Hard delete scope by name (cascades to API key scopes, first match)"""
        scope = await self.get_by_name(session, scope_name)
        
        if not scope:
            return False
        
        await session.delete(scope)
        await session.commit()
        return True
    
    async def hard_delete_by_id(
        self,
        session: AsyncSession,
        scope_id: int
    ) -> bool:
        """Hard delete scope by ID (cascades to API key scopes)"""
        scope = await self.get_by_id(session, scope_id)
        
        if not scope:
            return False
        
        await session.delete(scope)
        await session.commit()
        return True
    
    async def exists(
        self,
        session: AsyncSession,
        scope_name: str
    ) -> bool:
        """Check if scope exists"""
        scope = await self.get_by_name(session, scope_name)
        return scope is not None
    
    async def bulk_exists(
        self,
        session: AsyncSession,
        scope_names: List[str]
    ) -> dict:
        """Check which scopes exist from a list
        
        Returns: dict with scope_name as key and boolean as value
        """
        stmt = select(AKMScope.scope_name).where(
            AKMScope.scope_name.in_(scope_names),
            AKMScope.is_active == True
        )
        result = await session.execute(stmt)
        existing = {name for name in result.scalars().all()}
        
        return {name: name in existing for name in scope_names}
    
    async def bulk_upsert(
        self,
        session: AsyncSession,
        project_id: int,
        scopes_data: List[dict]
    ) -> dict:
        """Bulk upsert scopes for a project (create new or update existing)
        
        Args:
            project_id: Project ID to associate scopes with
            scopes_data: List of dicts with keys: scope_name, description, category, is_active
            
        Returns:
            dict with keys: created, updated, skipped, errors, scope_names
        """
        result = {
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "errors": [],
            "scope_names": []
        }
        
        for scope_data in scopes_data:
            try:
                scope_name = scope_data["scope_name"]
                description = scope_data.get("description", "")
                is_active = scope_data.get("is_active", True)
                
                # Check if scope exists in this project
                existing = await self.get_by_project_and_name(session, project_id, scope_name)
                
                if existing:
                    # Check if update is needed
                    needs_update = False
                    
                    if existing.description != description:
                        existing.description = description
                        needs_update = True
                    
                    if existing.is_active != is_active:
                        existing.is_active = is_active
                        needs_update = True
                    
                    if needs_update:
                        result["updated"] += 1
                        result["scope_names"].append(scope_name)
                    else:
                        result["skipped"] += 1
                else:
                    # Create new scope
                    new_scope = AKMScope(
                        project_id=project_id,
                        scope_name=scope_name,
                        description=description,
                        is_active=is_active
                    )
                    session.add(new_scope)
                    result["created"] += 1
                    result["scope_names"].append(scope_name)
                
            except Exception as e:
                result["errors"].append(f"Error processing scope '{scope_data.get('scope_name', 'unknown')}': {str(e)}")
                continue
        
        # Commit all changes
        if result["created"] > 0 or result["updated"] > 0:
            await session.commit()
        
        return result


# Singleton instance
scope_repository = ScopeRepository()
