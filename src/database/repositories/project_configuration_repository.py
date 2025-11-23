"""
Repository for Project Configuration operations.

Handles CRUD operations for dynamic project configurations including
CORS origins, rate limits, IP allowlists, and custom settings.
"""

from typing import Optional, Dict, Any, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.database.models import AKMProjectConfiguration, AKMProject
from src.logging_config import get_logger, log_with_context

logger = get_logger(__name__)


class ProjectConfigurationRepository:
    """Repository for managing project configurations"""
    
    async def get_by_project_id(
        self, 
        session: AsyncSession, 
        project_id: int
    ) -> Optional[AKMProjectConfiguration]:
        """
        Get configuration for a specific project (async).
        
        Args:
            session: Database session
            project_id: Project ID
            
        Returns:
            Project configuration or None if not found
        """
        try:
            result = await session.execute(
                select(AKMProjectConfiguration)
                .where(AKMProjectConfiguration.project_id == project_id)
            )
            config = result.scalar_one_or_none()
            
            if config:
                log_with_context(
                    logger, "debug", "Project configuration retrieved",
                    project_id=project_id,
                    has_cors=config.cors_origins is not None,
                    has_ip_allowlist=config.ip_allowlist is not None
                )
            
            return config
            
        except Exception as e:
            log_with_context(
                logger, "error", "Failed to get project configuration",
                project_id=project_id, error=str(e)
            )
            raise
    
    def get_by_project_id_sync(
        self, 
        session: Session, 
        project_id: int
    ) -> Optional[AKMProjectConfiguration]:
        """
        Get configuration for a specific project (sync version for middleware).
        
        Args:
            session: Database session
            project_id: Project ID
            
        Returns:
            Project configuration or None if not found
        """
        try:
            result = session.execute(
                select(AKMProjectConfiguration)
                .where(AKMProjectConfiguration.project_id == project_id)
            )
            config = result.scalar_one_or_none()
            
            return config
            
        except Exception as e:
            logger.error(f"Failed to get project configuration: {e}")
            return None
    
    async def create_or_update(
        self,
        session: AsyncSession,
        project_id: int,
        config_data: Dict[str, Any]
    ) -> AKMProjectConfiguration:
        """
        Create or update project configuration.
        
        Args:
            session: Database session
            project_id: Project ID
            config_data: Configuration data dictionary
            
        Returns:
            Created or updated configuration
        """
        try:
            # Check if configuration exists
            existing = await self.get_by_project_id(session, project_id)
            
            if existing:
                # Update existing configuration
                for key, value in config_data.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                
                await session.commit()
                await session.refresh(existing)
                
                log_with_context(
                    logger, "info", "Project configuration updated",
                    project_id=project_id,
                    updated_fields=list(config_data.keys())
                )
                
                return existing
            else:
                # Create new configuration
                config = AKMProjectConfiguration(
                    project_id=project_id,
                    **config_data
                )
                
                session.add(config)
                await session.commit()
                await session.refresh(config)
                
                log_with_context(
                    logger, "info", "Project configuration created",
                    project_id=project_id,
                    config_id=config.id
                )
                
                return config
                
        except Exception as e:
            await session.rollback()
            log_with_context(
                logger, "error", "Failed to create/update project configuration",
                project_id=project_id, error=str(e)
            )
            raise
    
    async def delete(
        self,
        session: AsyncSession,
        project_id: int
    ) -> bool:
        """
        Delete project configuration (reset to defaults).
        
        Args:
            session: Database session
            project_id: Project ID
            
        Returns:
            True if deleted, False if not found
        """
        try:
            config = await self.get_by_project_id(session, project_id)
            
            if not config:
                return False
            
            await session.delete(config)
            await session.commit()
            
            log_with_context(
                logger, "info", "Project configuration deleted",
                project_id=project_id
            )
            
            return True
            
        except Exception as e:
            await session.rollback()
            log_with_context(
                logger, "error", "Failed to delete project configuration",
                project_id=project_id, error=str(e)
            )
            raise
    
    async def validate_cors_origins(self, origins: List[str]) -> bool:
        """
        Validate CORS origins format.
        
        Args:
            origins: List of origin URLs
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If any origin is invalid
        """
        import re
        
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:[a-zA-Z0-9-]+\.)*[a-zA-Z0-9-]+'  # domain
            r'(?::\d+)?'  # optional port
            r'(?:/.*)?$'  # optional path
        )
        
        for origin in origins:
            # Allow localhost with port
            if origin.startswith('http://localhost') or origin.startswith('http://127.0.0.1'):
                continue
            
            # Disallow wildcard
            if origin == '*':
                raise ValueError("Wildcard (*) is not allowed for CORS origins. List each origin explicitly.")
            
            # Validate URL format
            if not url_pattern.match(origin):
                raise ValueError(f"Invalid origin format: {origin}")
        
        return True
    
    async def validate_ip_allowlist(self, ip_list: List[str]) -> bool:
        """
        Validate IP addresses and CIDR ranges.
        
        Args:
            ip_list: List of IP addresses or CIDR ranges
            
        Returns:
            True if valid
            
        Raises:
            ValueError: If any IP/CIDR is invalid
        """
        import ipaddress
        
        for ip_str in ip_list:
            try:
                # Try to parse as IP network (supports both single IPs and CIDR)
                ipaddress.ip_network(ip_str, strict=False)
            except ValueError as e:
                raise ValueError(f"Invalid IP address or CIDR range: {ip_str}") from e
        
        return True


# Create repository instance
project_configuration_repository = ProjectConfigurationRepository()
