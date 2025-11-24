from pathlib import Path
from datetime import datetime
import uuid
import traceback
from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import time

from src.api import (
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
    project_configurations_router,
)
# Import v1 API router
from src.api.v1 import v1_router
from src.api.versioning import LATEST_VERSION, get_deprecation_warning
from src.middleware import RateLimitMiddleware, VersioningMiddleware
from src.middleware.audit import AuditMiddleware
from src.middleware.cors import DynamicCORSMiddleware
from src.config import settings
from src.logging_config import get_logger, log_with_context

# Initialize logger
logger = get_logger(__name__)

# Log application startup
log_with_context(
    logger,
    'info',
    'Initializing API Key Management Service',
    version=settings.api_version,
    environment=settings.environment,
    betterstack_enabled=settings.betterstack_enabled
)

# Create FastAPI application with security scheme
app = FastAPI(
    title="API Key Management Service",
    description="""
**API Key Management and Authentication Service**

Production-ready FastAPI application com multi-tenancy, RBAC, rate limiting, webhooks e audit logging.

**Principais recursos:**
- Multi-tenant project isolation
- Secure API key management (SHA-256)
- 30+ granular permission scopes
- Rate limiting and IP restrictions
- Webhook integrations (HMAC)
- Real-time monitoring and alerting
- Sensitive data sanitization

[Guias de Implementação](/static/guides/index.html)

[Collection de Postman](https://www.postman.com/flavio-lopes-a2e55a26-6064350/ideias-factory-tech-public-workspace/collection/fv59rll/api-key-management-service?action=share&creator=50302320)

[![Run in Postman](https://run.pstmn.io/button.svg)](https://god.gw.postman.com/run-collection/:collection_id?action=collection%2Ffork&source=rip_markdown&:collection_url)

""",
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "Health",
            "description": "Health check endpoints for monitoring",
        },
        {
            "name": "Home",
            "description": "Home page and general information",
        },
        {
            "name": "Projects",
            "description": "Project management for multi-tenant API keys",
        },
        {
            "name": "API Keys",
            "description": "API Key creation and management",
            "externalDocs": {
                "description": "🔑 Authentication Guide",
                "url": "https://akm.ideiasfactory.tech/public/guides/authentication.html"
            }
        },
        {
            "name": "Scopes",
            "description": "Permission scope management",
            "externalDocs": {
                "description": "📖 Bulk Insert Documentation",
                "url": "https://akm.ideiasfactory.tech/public/guides/scopes_bulk_insert.html"
            }
        },
        {
            "name": "Webhooks",
            "description": "Webhook configuration and event subscriptions",
            "externalDocs": {
                "description": "🔔 Webhooks Documentation",
                "url": "https://akm.ideiasfactory.tech/public/guides/webhooks.html"
            }
        },
        {
            "name": "API Key Configuration",
            "description": "Rate limits, IP restrictions, and usage statistics",
        },
        {
            "name": "Alerts",
            "description": "Alert rule management and monitoring",
        },
        {
            "name": "OpenAPI Scope Generation",
            "description": "Generate scopes from OpenAPI/Swagger specifications",
        },
        {
            "name": "Audit Logs",
            "description": "Audit trail and integrity verification (read-only)",
            "externalDocs": {
                "description": "📊 Audit & Logging Guide",
                "url": "https://akm.ideiasfactory.tech/public/operation/logging.html"
            }
        },
        {
            "name": "Sensitive Fields",
            "description": "Manage sensitive field sanitization rules",
            "externalDocs": {
                "description": "📖 Sensitive Fields Guide",
                "url": "https://akm.ideiasfactory.tech/public/admin/sensitive_fields.html"
            }
        },
        {
            "name": "Project Configurations",
            "description": "Dynamic project configuration (CORS, rate limits, IP allowlist, webhooks)",
        },
    ],
)


def custom_openapi():
    """Custom OpenAPI schema with API Key security."""
    try:
        if app.openapi_schema:
            return app.openapi_schema
        from fastapi.openapi.utils import get_openapi
        openapi_schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags
        )
        # Adiciona externalDocs global
        openapi_schema["externalDocs"] = {
            "description": "Documentação Completa HTML",
            "url": "/static/docs_index.html"
        }
        # Add security scheme for API Key authentication
        openapi_schema["components"]["securitySchemes"] = {
            "APIKeyHeader": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
                "description": "API Key for authentication. Use the management scripts to create and manage keys."
            }
        }
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    except Exception as exc:
        import traceback
        print("[ERROR] custom_openapi exception:", exc)
        print(traceback.format_exc())
        # Optionally, log to file or external service here
        return {
            "error": "Failed to generate OpenAPI schema.",
            "exception": str(exc),
            "trace": traceback.format_exc()
        }


app.openapi = custom_openapi


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Custom exception handler for HTTPException to return standardized error format."""
    
    # Get correlation_id from request state
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    
    # Determine status type based on status code
    if 400 <= exc.status_code < 500:
        status_type = "client_error"
    elif 500 <= exc.status_code < 600:
        status_type = "error"
    else:
        status_type = "error"
    
    # Get query parameters to log invalid data
    query_params = dict(request.query_params) if request.query_params else {}
    
    # Log com stacktrace se for erro 500
    log_context = {
        "correlation_id": correlation_id,
        "status_code": exc.status_code,
        "path": request.url.path,
        "method": request.method,
        "query_params": query_params if query_params else None
    }
    
    # Capturar stacktrace SOMENTE para erros 5xx conforme requisição
    if exc.status_code >= 500:
        log_context["stacktrace"] = traceback.format_exc()
    
    # Escala alguns códigos (401,403,404) para ERROR se quiser maior visibilidade
    if status_type == "client_error" and exc.status_code in (401, 403):
        level = 'error'
    else:
        level = 'warning' if status_type == "client_error" else 'error'

    # Incluir stacktrace no corpo apenas se presente (erros 5xx)
    message = f"HTTP Exception: {exc.detail}"
    if "stacktrace" in log_context:
        message = message + "\n" + log_context["stacktrace"].rstrip()

    log_with_context(
        logger,
        level,
        message,
        **log_context
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": status_type,
            "correlation_id": correlation_id,
            "data": None,
            "error_message": exc.detail,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors (500 Internal Server Error)."""  
    # Get correlation_id from request state
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    
    # Captura stacktrace completo
    stack_trace = traceback.format_exc()
    
    # Incluir stacktrace diretamente na mensagem para aparecer no console em qualquer ambiente
    message = f"Internal Server Error: {str(exc)}\n{stack_trace.rstrip()}"
    log_with_context(
        logger,
        'error',
        message,
        correlation_id=correlation_id,
        status_code=500,
        path=request.url.path,
        method=request.method,
        error_type=type(exc).__name__,
        stacktrace=stack_trace
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "correlation_id": correlation_id,
            "data": None,
            "error_message": "Internal Server Error. Please contact support with the correlation_id.",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Custom exception handler for request validation errors."""
    
    # Get correlation_id from request state
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    
    # Format validation errors in a friendly way
    errors = exc.errors()
    error_messages = []
    error_details = []
    
    for error in errors:
        field = " -> ".join(str(loc) for loc in error["loc"])
        msg = error["msg"]
        error_messages.append(f"{field}: {msg}")
        error_details.append({
            "field": field,
            "message": msg,
            "input": error.get("input"),
            "type": error.get("type")
        })
    
    error_detail = "; ".join(error_messages)
    
    # Get query parameters and body to log invalid data
    query_params = dict(request.query_params) if request.query_params else {}
    
    log_with_context(
        logger,
        'warning',
        f"Validation error: {error_detail}",
        correlation_id=correlation_id,
        path=request.url.path,
        method=request.method,
        query_params=query_params if query_params else None,
        validation_errors=error_details
    )
    
    return JSONResponse(
        status_code=422,
        content={
            "status": "client_error",
            "correlation_id": correlation_id,
            "data": None,
            "error_message": f"Validation error: {error_detail}",
            "timestamp": datetime.utcnow().isoformat()
        }
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware to log all HTTP requests with timing."""
    start_time = time.time()
    
    # Get correlation_id from request state (set by correlation_id_middleware)
    correlation_id = getattr(request.state, "correlation_id", "unknown")
    
    # Log incoming request
    log_with_context(
        logger,
        'info',
        f"Incoming request: {request.method} {request.url.path}",
        correlation_id=correlation_id,
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else None,
        user_agent=request.headers.get('user-agent', 'unknown')
    )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log response
    log_with_context(
        logger,
        'info',
        f"Request completed: {request.method} {request.url.path}",
        correlation_id=correlation_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_seconds=round(duration, 4)
    )
    
    return response


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Middleware to add correlation_id to all requests. Must be declared last to run first."""
    # Get correlation_id from header or generate new one
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    
    # Store correlation_id in request state for access in routes
    request.state.correlation_id = correlation_id
    
    # Process request
    response = await call_next(request)
    
    # Add correlation_id to response headers
    response.headers["X-Correlation-ID"] = correlation_id
    
    return response


# Configure Dynamic CORS (project-specific origins)
app.add_middleware(DynamicCORSMiddleware)

# Add audit middleware (before rate limiting)
app.add_middleware(AuditMiddleware)
# Add versioning middleware (to add deprecation headers)
app.add_middleware(VersioningMiddleware)


# Add rate limiting middleware
app.add_middleware(RateLimitMiddleware)

# Mount static files (for favicon and other public assets)
public_dir = Path(__file__).parent / "public"
logger.info("Checking for public directory at %s", str(public_dir))
if public_dir.exists():
    app.mount("/static", StaticFiles(directory=str(public_dir)), name="static")
    admin_guide_path = public_dir / "admin"
    logger.info("Checking for administration at %s", str(admin_guide_path))
    if admin_guide_path.exists():
        logger.info("Administration guide found at %s", str(admin_guide_path))
        app.mount("/admin", StaticFiles(directory=str(admin_guide_path), html=True), name="admin")


# Include routers
app.include_router(home_router)  # Includes GET / for home page
app.include_router(health_router)  # Includes /health endpoints

# Include versioned API routes
# v1 API with /akm/v1 prefix
app.include_router(v1_router, prefix="/akm")

# Legacy support: Include unversioned routes (defaults to v1 behavior)
# These routes will be deprecated in the future
akm_prefix = "/akm"
app.include_router(projects_router, prefix=akm_prefix, include_in_schema=False)
app.include_router(keys_router, prefix=akm_prefix, include_in_schema=False)
app.include_router(scopes_router, prefix=akm_prefix, include_in_schema=False)
app.include_router(webhooks_router, prefix=akm_prefix, include_in_schema=False)
app.include_router(configs_router, prefix=akm_prefix, include_in_schema=False)
app.include_router(alerts_router, prefix=akm_prefix, include_in_schema=False)
app.include_router(openapi_scopes_router, prefix=akm_prefix, include_in_schema=False)
app.include_router(audit_router, prefix=akm_prefix, include_in_schema=False)
app.include_router(sensitive_fields_router, prefix=akm_prefix, include_in_schema=False)
app.include_router(project_configurations_router, prefix=akm_prefix, include_in_schema=False)

# Log application ready
log_with_context(
    logger,
    'info',
    'API Key Management Service ready',
    routes_count=len(app.routes),
    latest_api_version=LATEST_VERSION.value,
    versioned_prefix="/akm/v1",
    legacy_prefix="/akm (deprecated)"
)

if __name__ == "__main__":
    import uvicorn

    # Option A – pass the object directly (cleanest if `app` is defined in this file)
    uvicorn.run(
        "main:app",          # or just `app` if you prefer
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_excludes=[".git", "__pycache__", ".venv"]
    )
