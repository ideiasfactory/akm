"""API Key authentication middleware and dependencies."""

from typing import Optional
from fastapi import Header, HTTPException, status, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import get_session
from src.database.repositories.api_key_repository import APIKeyRepository
from src.logging_config import get_logger

logger = get_logger(__name__)


async def verify_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> str:
    """
    Verify API key from request header.

    Args:
        x_api_key: API key from X-API-Key header
        request: FastAPI request object
        session: Database session from dependency injection

    Returns:
        API key name if valid

    Raises:
        HTTPException: If API key is missing or invalid
    """
    correlation_id = (
        getattr(request.state, "correlation_id", "unknown") if request else "unknown"
    )

    if not x_api_key:
        logger.warning(
            "Missing API key in request",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path if request else "unknown",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include X-API-Key header in your request.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Validate the key
    repo = APIKeyRepository(session)
    api_key_record = await repo.validate_key(x_api_key)

    if api_key_record is None:
        logger.warning(
            "Invalid API key used",
            extra={
                "correlation_id": correlation_id,
                "path": request.url.path if request else "unknown",
                "key_prefix": x_api_key[:8] if x_api_key else "none",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Store API key info in request state for logging
    if request:
        request.state.api_key_name = api_key_record.name
        request.state.api_key_id = api_key_record.id

    logger.info(
        f"API key authenticated: {api_key_record.name}",
        extra={
            "correlation_id": correlation_id,
            "api_key_name": api_key_record.name,
            "api_key_id": api_key_record.id,
            "request_count": api_key_record.request_count,
        },
    )

    return str(api_key_record.name)


async def optional_api_key(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    session: AsyncSession = Depends(get_session),
) -> Optional[str]:
    """
    Optional API key verification (doesn't raise exception if missing).

    Useful for endpoints that have both public and authenticated access.

    Args:
        request: FastAPI request object
        x_api_key: API key from X-API-Key header
        session: Database session from dependency injection

    Returns:
        API key name if valid, None otherwise
    """
    if not x_api_key:
        return None

    try:
        return await verify_api_key(request, x_api_key, session)
    except HTTPException:
        return None
