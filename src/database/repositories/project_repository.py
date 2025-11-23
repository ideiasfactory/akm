"""
Repository for Project operations.

Handles CRUD operations for projects in the multi-tenant API key management system.
"""

from typing import List, Optional
from datetime import datetime

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.database.models import AKMProject, AKMAPIKey


class ProjectRepository:
    """Repository for project management operations"""
    
    async def create(
        self,
        session: AsyncSession,
        name: str,
        description: Optional[str] = None
    ) -> AKMProject:
        """Create a new project"""
        project = AKMProject(
            name=name,
            description=description,
            is_active=True
        )
        
        session.add(project)
        await session.commit()
        await session.refresh(project)
        
        return project
    
    async def get_by_id(
        self,
        session: AsyncSession,
        project_id: int
    ) -> Optional[AKMProject]:
        """Get project by ID"""
        stmt = select(AKMProject).where(AKMProject.id == project_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_name(
        self,
        session: AsyncSession,
        name: str
    ) -> Optional[AKMProject]:
        """Get project by name"""
        stmt = select(AKMProject).where(AKMProject.name == name)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def list_all(
        self,
        session: AsyncSession,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[AKMProject]:
        """List all projects with pagination"""
        stmt = select(AKMProject)
        
        if active_only:
            stmt = stmt.where(AKMProject.is_active == True)
        
        stmt = stmt.offset(skip).limit(limit).order_by(AKMProject.created_at.desc())
        
        result = await session.execute(stmt)
        return list(result.scalars().all())
    
    async def update(
        self,
        session: AsyncSession,
        project_id: int,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Optional[AKMProject]:
        """Update project"""
        project = await self.get_by_id(session, project_id)
        
        if not project:
            return None
        
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        if is_active is not None:
            project.is_active = is_active
        
        project.updated_at = datetime.utcnow()
        
        await session.commit()
        await session.refresh(project)
        
        return project
    
    async def delete(
        self,
        session: AsyncSession,
        project_id: int
    ) -> bool:
        """Delete project (soft delete - deactivate)"""
        project = await self.get_by_id(session, project_id)
        
        if not project:
            return False
        
        project.is_active = False
        project.updated_at = datetime.utcnow()
        
        await session.commit()
        return True
    
    async def hard_delete(
        self,
        session: AsyncSession,
        project_id: int
    ) -> bool:
        """Hard delete project (cascades to API keys)"""
        project = await self.get_by_id(session, project_id)
        
        if not project:
            return False
        
        await session.delete(project)
        await session.commit()
        return True
    
    async def get_api_key_count(
        self,
        session: AsyncSession,
        project_id: int,
        active_only: bool = True
    ) -> int:
        """Get count of API keys in project"""
        stmt = select(AKMAPIKey).where(AKMAPIKey.project_id == project_id)
        
        if active_only:
            stmt = stmt.where(AKMAPIKey.is_active == True)
        
        result = await session.execute(stmt)
        return len(list(result.scalars().all()))
    
    async def get_with_keys(
        self,
        session: AsyncSession,
        project_id: int
    ) -> Optional[AKMProject]:
        """Get project with all API keys loaded"""
        stmt = select(AKMProject).where(
            AKMProject.id == project_id
        ).options(selectinload(AKMProject.api_keys))
        
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


# Singleton instance
project_repository = ProjectRepository()
