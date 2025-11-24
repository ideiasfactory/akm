"""
API endpoints for Project Configuration management.

Handles dynamic configuration for CORS, rate limits, IP allowlists, and custom settings.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.database.repositories.project_configuration_repository import project_configuration_repository
from src.database.models import AKMAPIKey
from src.api.auth_middleware import PermissionChecker
from src.api.models.project_configuration import (
    ProjectConfigurationCreate,
    ProjectConfigurationUpdate,
    ProjectConfigurationResponse,
    ProjectConfigurationDeleteResponse
)
from src.logging_config import get_logger, log_with_context

logger = get_logger(__name__)

router = APIRouter(tags=["Project Configurations"])


@router.put(
    "/projects/{project_id}/configuration",
    response_model=ProjectConfigurationResponse,
    status_code=status.HTTP_200_OK,
    summary="Create or update project configuration",
    description="Create or update dynamic configuration for a project. Requires 'akm:projects:write' scope."
)
async def upsert_project_configuration(
    project_id: int,
    config: ProjectConfigurationCreate,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:projects:write"])),
    session: AsyncSession = Depends(get_session)
):
    """
    Create or update project configuration.
    
    **Supported configurations:**
    - CORS origins (list of URLs)
    - Default rate limits (per minute/hour/day/month)
    - IP allowlist (CIDR notation)
    - Webhook settings (timeout, retries)
    - Custom sensitive fields
    
    **Configuration priority:**
    1. API Key level (highest)
    2. Project level (this configuration)
    3. Global defaults (lowest)
    
    Changes apply immediately without restart.
    """
    try:
        # Verify API key belongs to this project or has admin access
        # api_key is already authenticated by PermissionChecker
        
        # Check if API key has access to this project
        if api_key.project_id != project_id:
            # Check if API key has admin scope for cross-project access
            scopes = [scope.scope_name for scope in api_key.scopes]
            if "akm:admin" not in scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="API key does not have access to this project"
                )
        
        # Convert Pydantic model to dict (only non-None values)
        config_data = config.model_dump(exclude_none=True)
        
        # Create or update configuration
        db_config = await project_configuration_repository.create_or_update(
            session=session,
            project_id=project_id,
            config_data=config_data
        )
        
        log_with_context(
            logger, "info", "Project configuration updated via API",
            project_id=project_id,
            api_key_id=api_key.id,
            updated_fields=list(config_data.keys())
        )
        
        return ProjectConfigurationResponse.model_validate(db_config)
        
    except ValueError as e:
        # Validation errors from repository
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        log_with_context(
            logger, "error", "Failed to upsert project configuration",
            project_id=project_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update project configuration"
        )


@router.get(
    "/projects/{project_id}/configuration",
    response_model=Optional[ProjectConfigurationResponse],
    status_code=status.HTTP_200_OK,
    summary="Get project configuration",
    description="Retrieve current configuration for a project. Requires 'akm:projects:read' scope."
)
async def get_project_configuration(
    project_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:projects:read"])),
    session: AsyncSession = Depends(get_session)
):
    """
    Get project configuration.
    
    Returns the current dynamic configuration for this project.
    If no custom configuration exists, returns null (project uses global defaults).
    """
    try:
        # Verify API key belongs to this project or has admin access
        # api_key is already authenticated by PermissionChecker
        
        # Check if API key has access to this project
        if api_key.project_id != project_id:
            # Check if API key has admin scope for cross-project access
            scopes = [scope.scope_name for scope in api_key.scopes]
            if "akm:admin" not in scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="API key does not have access to this project"
                )
        
        # Get configuration
        config = await project_configuration_repository.get_by_project_id(
            session=session,
            project_id=project_id
        )
        
        if not config:
            return None
        
        return ProjectConfigurationResponse.model_validate(config)
        
    except HTTPException:
        raise
    except Exception as e:
        log_with_context(
            logger, "error", "Failed to get project configuration",
            project_id=project_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve project configuration"
        )


@router.delete(
    "/projects/{project_id}/configuration",
    response_model=ProjectConfigurationDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete project configuration",
    description="Delete project configuration (reset to global defaults). Requires 'akm:projects:write' scope."
)
async def delete_project_configuration(
    project_id: int,
    api_key: AKMAPIKey = Depends(PermissionChecker(["akm:projects:write"])),
    session: AsyncSession = Depends(get_session)
):
    """
    Delete project configuration.
    
    Removes custom configuration for this project.
    Project will use global defaults after deletion.
    """
    try:
        # Verify API key belongs to this project or has admin access
        # api_key is already authenticated by PermissionChecker
        
        # Check if API key has access to this project
        if api_key.project_id != project_id:
            # Check if API key has admin scope for cross-project access
            scopes = [scope.scope_name for scope in api_key.scopes]
            if "akm:admin" not in scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="API key does not have access to this project"
                )
        
        # Delete configuration
        deleted = await project_configuration_repository.delete(
            session=session,
            project_id=project_id
        )
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project configuration not found"
            )
        
        log_with_context(
            logger, "info", "Project configuration deleted via API",
            project_id=project_id,
            api_key_id=api_key.id
        )
        
        return ProjectConfigurationDeleteResponse(
            success=True,
            message="Project configuration deleted successfully. Project will use global defaults.",
            project_id=project_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_with_context(
            logger, "error", "Failed to delete project configuration",
            project_id=project_id, error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete project configuration"
        )
