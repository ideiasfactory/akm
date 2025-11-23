from datetime import datetime
from time import time
import os
from pathlib import Path
from typing import Dict, Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ..models.health import HealthResponse, DatabaseStatus
from src.config import settings
from src.logging_config import get_logger, log_with_context
from src.database.connection import get_async_session

# Initialize logger
logger = get_logger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])

# Track application start time for uptime calculation
_start_time = time()

# Log health router initialization
log_with_context(logger, "info", "Health router initialized", start_time=_start_time)


async def get_database_status() -> DatabaseStatus:
    """
    Check database connection status.
    """
    # Sempre usar o banco (Neon) se DATABASE_URL estiver configurado
    # (antes ficava restrito a production e caía em modo CSV em dev)
    use_database = bool(settings.database_url)

    if use_database:
        # Database mode - basic connection check
        try:
            log_with_context(logger, "debug", "Starting database health check")

            start_time = time()

            async with get_async_session() as session:
                # Simple connection test
                await session.execute(text("SELECT 1"))
                records_count = 0
                last_updated = None

            latency = round((time() - start_time) * 1000, 2)  # Convert to ms

            db_status = DatabaseStatus(
                connected=True,
                type="postgresql",
                latency_ms=latency,
                records_count=records_count,
                last_updated=last_updated,
            )

            log_with_context(
                logger,
                "info",
                "Database health check successful",
                connected=db_status.connected,
                db_type=db_status.type,
                records_count=records_count,
                latency_ms=latency,
            )

            return db_status

        except Exception as e:
            log_with_context(
                logger,
                "error",
                "Database health check failed",
                error=str(e),
                error_type=type(e).__name__,
            )

            return DatabaseStatus(
                connected=False,
                type="postgresql",
                latency_ms=None,
                records_count=None,
                last_updated=None,
            )
    else:
        # Sem DATABASE_URL configurada - sem dados
        log_with_context(logger, "debug", "No database configured")
        
        return DatabaseStatus(
            connected=False,
            type=None,
            latency_ms=None,
            records_count=None,
            last_updated=None,
        )


@router.get("/", response_model=HealthResponse, summary="Health Check")
async def health_check(
    db_status: DatabaseStatus = Depends(get_database_status),
) -> HealthResponse:
    """
    Get API health status.

    Returns comprehensive health information including:
    - Overall API status
    - Version and environment
    - Current timestamp and uptime
    - Database connection status

    Returns:
        HealthResponse: Detailed health information
    """
    uptime = time() - _start_time

    # Determine overall status based on database connection
    if db_status.connected:
        status = "healthy"
        log_with_context(
            logger,
            "info",
            "Health check: System healthy",
            status=status,
            uptime_seconds=round(uptime, 2),
            db_connected=db_status.connected,
        )
    else:
        status = "degraded"
        log_with_context(
            logger,
            "warning",
            "Health check: System degraded - database not connected",
            status=status,
            uptime_seconds=round(uptime, 2),
            db_connected=db_status.connected,
        )

    return HealthResponse(
        status=status,
        version=settings.api_version,
        environment=settings.environment,
        timestamp=datetime.utcnow(),
        uptime_seconds=uptime,
        database=db_status,
    )


@router.get("/liveness", summary="Liveness Probe")
async def liveness_check() -> JSONResponse:
    """
    Simple liveness check for container orchestration.

    Returns 200 if the service is running, regardless of dependencies.
    Useful for Kubernetes liveness probes.

    Returns:
        JSONResponse: Simple alive status
    """
    log_with_context(logger, "debug", "Liveness probe check")

    return JSONResponse(
        status_code=200,
        content={"status": "alive", "timestamp": datetime.utcnow().isoformat()},
    )


@router.get("/readiness", summary="Readiness Probe")
async def readiness_check(
    db_status: DatabaseStatus = Depends(get_database_status),
) -> JSONResponse:
    """
    Readiness check for container orchestration.

    Returns 200 if the service is ready to accept traffic (database connected).
    Returns 503 if not ready. Useful for Kubernetes readiness probes.

    Returns:
        JSONResponse: Readiness status
    """
    if db_status.connected:
        log_with_context(
            logger,
            "info",
            "Readiness probe: Service ready",
            db_connected=db_status.connected,
        )

        return JSONResponse(
            status_code=200,
            content={
                "status": "ready",
                "timestamp": datetime.utcnow().isoformat(),
                "database": "connected",
            },
        )
    else:
        log_with_context(
            logger,
            "warning",
            "Readiness probe: Service not ready - database disconnected",
            db_connected=db_status.connected,
        )

        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "timestamp": datetime.utcnow().isoformat(),
                "database": "disconnected",
            },
        )
