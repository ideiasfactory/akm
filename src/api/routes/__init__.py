from .health import router as health_router
from .home import router as home_router
from .projects import router as projects_router
from .keys import router as keys_router
from .scopes import router as scopes_router
from .webhooks import router as webhooks_router
from .configs import router as configs_router
from .alerts import router as alerts_router
from .openapi_scopes import router as openapi_scopes_router
from .audit import router as audit_router
from .sensitive_fields import router as sensitive_fields_router
from .project_configurations import router as project_configurations_router

__all__ = [
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
    "project_configurations_router",
]
