"""
API v1 Routes
Re-export all routes from the main routes directory for v1 compatibility.
"""

from src.api.routes.projects import router as projects_router
from src.api.routes.keys import router as keys_router
from src.api.routes.scopes import router as scopes_router
from src.api.routes.webhooks import router as webhooks_router
from src.api.routes.configs import router as configs_router
from src.api.routes.alerts import router as alerts_router
from src.api.routes.openapi_scopes import router as openapi_scopes_router
from src.api.routes.audit import router as audit_router
from src.api.routes.sensitive_fields import router as sensitive_fields_router

__all__ = [
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
