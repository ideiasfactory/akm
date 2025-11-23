"""
API v1 Package
"""

from fastapi import APIRouter
from .routes import (
    health_router,
    home_router,
    projects_router,
    keys_router,
    scopes_router,
    webhooks_router,
    configs_router,
    alerts_router,
    openapi_scopes_router,
    audit_router,
    sensitive_fields_router,
)

# Create v1 API router
v1_router = APIRouter(prefix="/v1")

# Include all v1 routes
v1_router.include_router(health_router)
v1_router.include_router(home_router)
v1_router.include_router(projects_router)
v1_router.include_router(keys_router)
v1_router.include_router(scopes_router)
v1_router.include_router(webhooks_router)
v1_router.include_router(configs_router)
v1_router.include_router(alerts_router)
v1_router.include_router(openapi_scopes_router)
v1_router.include_router(audit_router)
v1_router.include_router(sensitive_fields_router)

__all__ = [
    "v1_router",
    "health_router",
    "home_router",
    "projects_router",
    "keys_router",
    "scopes_router",
    "webhooks_router",
    "configs_router",
    "alerts_router",
    "openapi_scopes_router",
    "audit_router",
    "sensitive_fields_router",
]
