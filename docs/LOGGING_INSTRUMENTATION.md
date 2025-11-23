# Logging Instrumentation Summary

## Overview
This document describes the comprehensive logging instrumentation added to the Brazilian CDS Data Feeder API v2.0.0.

## Instrumented Files

### 1. **main.py** - Application Entry Point
**Logging Added:**
- ✅ Application startup with context (version, environment, BetterStack status)
- ✅ HTTP request middleware logging all incoming requests
- ✅ Request logging includes: method, path, client IP, user agent, status code, duration

**Key Log Events:**
```python
# Startup
logger.info("Application starting", extra={"context": {...}})

# HTTP Requests (all endpoints)
logger.info(f"HTTP {method} {url.path} - {status_code} ({duration:.3f}s)")
```

---

### 2. **src/api/routes/health.py** - Health Check Endpoints
**Logging Added:**
- ✅ Router initialization
- ✅ Database health check attempts (debug)
- ✅ Successful database connections (info)
- ✅ Failed database connections (error with exception details)
- ✅ Overall health status (info for healthy, warning for degraded)
- ✅ Liveness probe checks (debug)
- ✅ Readiness probe results (info for ready, warning for not ready)

**Key Log Events:**
```python
# Health Check
logger.info("Health check: System healthy", extra={"context": {...}})
logger.warning("Health check: System degraded - database not connected")

# Database Status
logger.info("Database health check successful")
logger.error("Database health check failed", extra={"context": {"error": ...}})

# Readiness Probe
logger.info("Readiness probe: Service ready")
logger.warning("Readiness probe: Service not ready - database disconnected")
```

---

### 3. **src/api/routes/home.py** - Home Page & Static Files
**Logging Added:**
- ✅ Template search process (debug)
- ✅ Successful template loading with path (info)
- ✅ Failed template reads (debug with error)
- ✅ Fallback to inline HTML (warning)
- ✅ Home page rendering attempts (debug with client IP)
- ✅ Successful page renders with content length (info)
- ✅ Home page data retrieval (info with counts)
- ✅ Favicon search and serving (info with path)
- ✅ Favicon not found (warning)
- ✅ All exceptions caught and logged (error with stack trace)

**Key Log Events:**
```python
# Template Loading
logger.info("Home template found and loaded", extra={"context": {"template_path": ...}})
logger.warning("Template not found - using fallback HTML")

# Page Rendering
logger.info("Home page rendered successfully", extra={"context": {"content_length": ...}})

# Favicon Serving
logger.info("Favicon found and served", extra={"context": {"path": ...}})
logger.warning("Favicon not found in any expected location")

# Errors
logger.error("Failed to render home page", extra={"context": {"error": ...}})
```

---

## Log Levels Usage

### INFO Level
- Successful operations (health checks, page renders, file serving)
- Router initialization
- Database connections established
- Readiness/liveness confirmations

### WARNING Level
- System degraded (database disconnected but API running)
- Service not ready (readiness probe fails)
- Template not found (using fallback)
- Resource not found (favicon missing)

### ERROR Level
- Database connection failures with exceptions
- Failed page rendering with stack traces
- Failed data retrieval with error details

### DEBUG Level
- Detailed operational info (template search paths)
- Liveness probe pings
- Database health check initiation
- Request context details

---

## Contextual Information Logged

All logs include rich context using `log_with_context()`:

### Health Endpoints
- `status`: Current health status
- `uptime_seconds`: Application uptime
- `db_connected`: Database connection status
- `db_type`: Type of database
- `error`: Exception messages
- `error_type`: Exception class names

### Home Endpoints
- `version`: API version
- `environment`: Deployment environment
- `template_path`: Resolved template location
- `content_length`: Size of rendered content
- `features_count`: Number of features displayed
- `endpoints_count`: Number of endpoints listed
- `client_ip`: Client IP address
- `path`: File paths for static resources

### HTTP Requests (Middleware)
- `method`: HTTP method (GET, POST, etc.)
- `path`: Request path
- `status_code`: Response status code
- `duration`: Request processing time in seconds
- `client_ip`: Client IP address
- `user_agent`: Client user agent string

---

## BetterStack Integration

### Production Environment
- All logs automatically sent to BetterStack (Logtail)
- Structured JSON format with metadata
- Includes: timestamp, level, message, context, environment, version

### Development Environment
- Logs output to console only
- Human-readable format
- BetterStack integration disabled

---

## Testing Recommendations

### Local Testing
```bash
# Start the server
uvicorn main:app --reload

# Test endpoints and observe console logs
curl http://localhost:8000/
curl http://localhost:8000/health
curl http://localhost:8000/health/liveness
curl http://localhost:8000/health/readiness
curl http://localhost:8000/api/home/data
curl http://localhost:8000/favicon.ico
```

### Production Testing (Vercel)
1. Deploy to Vercel
2. Access BetterStack dashboard
3. Filter logs by:
   - Level (info, warning, error)
   - Source (health, home, main)
   - Context fields (db_connected, status_code, etc.)

---

## Log Volume Estimates

### Typical Traffic Pattern
- **Startup**: 1 log entry
- **Health Check**: 3-4 log entries per request
- **Home Page**: 4-6 log entries per request
- **Favicon**: 2-3 log entries per request
- **HTTP Middleware**: 1 log entry per request

### Expected Daily Volume (1000 requests/day)
- ~5000-7000 log entries
- ~500KB compressed JSON (BetterStack)

---

## Next Steps

1. ✅ Health routes instrumented
2. ✅ Home routes instrumented  
3. ✅ Main app instrumented
4. ⏳ Test locally with uvicorn
5. ⏳ Deploy to Vercel
6. ⏳ Verify logs in BetterStack dashboard
7. ⏳ Monitor for any issues or performance impacts

---

## Configuration

Logging is configured via environment variables:

```env
# Required for production logging
BETTERSTACK_SOURCE_TOKEN=your_token_here
BETTERSTACK_INGESTING_HOST=in.logs.betterstack.com

# Optional - defaults
LOG_LEVEL=INFO
ENVIRONMENT=production  # Set to 'development' to disable BetterStack
```

---

## Maintenance

### Adding Logging to New Routes
```python
from src.logging_config import get_logger, log_with_context

logger = get_logger(__name__)

@router.get("/new-endpoint")
async def new_endpoint():
    try:
        log_with_context(logger, 'debug', 'Starting operation')
        
        # Your code here
        
        log_with_context(logger, 'info', 'Operation successful', result=...)
        return result
        
    except Exception as e:
        log_with_context(
            logger, 
            'error', 
            'Operation failed',
            error=str(e),
            error_type=type(e).__name__
        )
        raise
```

### Monitoring Key Metrics
- Error rate: `level:error`
- Response times: `duration` field in HTTP logs
- Database issues: `db_connected:false`
- Service health: `status:degraded` or `status:not_ready`

---

**Last Updated:** 2024 (during logging instrumentation)
**Author:** GitHub Copilot
**Version:** 1.0.0
