# API Structure

This directory contains the API routes and models for the API Key Management Service.

## Directory Structure

```
src/api/
├── __init__.py          # Main API module exports
├── models/              # Pydantic models for request/response validation
│   ├── __init__.py
│   ├── health.py       # Health check models
│   └── home.py         # Home page data models
└── routes/              # FastAPI route handlers
    ├── __init__.py
    ├── health.py       # Health check endpoints
    └── home.py         # Home page endpoints
```

## Models

### Health Models (`models/health.py`)

- **`DatabaseStatus`**: Database connection status information
  - `connected`: Boolean indicating database connectivity
  - `type`: Database type (postgresql, csv)
  - `latency_ms`: Query response latency
  - `records_count`: Total records in database
  - `last_updated`: Timestamp of last data update

- **`HealthResponse`**: Complete health check response
  - `status`: Overall status (healthy, degraded, unhealthy)
  - `version`: API version
  - `environment`: Deployment environment
  - `timestamp`: Current server time
  - `uptime_seconds`: Service uptime
  - `database`: DatabaseStatus object

### Home Models (`models/home.py`)

- **`FeatureInfo`**: Feature display information
  - `icon`: Emoji icon
  - `title`: Feature title
  - `description`: Feature description

- **`EndpointInfo`**: Endpoint documentation
  - `method`: HTTP method
  - `path`: Endpoint path
  - `description`: Endpoint description

- **`HomePageData`**: Complete home page data structure
  - `version`: API version
  - `environment`: Deployment environment
  - `features`: List of FeatureInfo
  - `endpoints`: List of EndpointInfo

## Routes

### Health Routes (`routes/health.py`)

- **`GET /health`**: Main health check endpoint
  - Returns comprehensive health information
  - Includes database status
  - Response: `HealthResponse`

- **`GET /health/liveness`**: Kubernetes liveness probe
  - Simple alive check
  - Always returns 200 if service is running

- **`GET /health/readiness`**: Kubernetes readiness probe
  - Checks if service can accept traffic
  - Returns 200 if ready, 503 if not ready
  - Depends on database connectivity

### Home Routes (`routes/home.py`)

- **`GET /`**: Home page endpoint
  - Serves the HTML home page
  - Replaces template placeholders with actual data
  - Returns: HTML response

- **`GET /api/home/data`**: Home page data API
  - Returns structured home page data as JSON
  - Useful for programmatic access
  - Response: `HomePageData`

## Usage in FastAPI Application

```python
from fastapi import FastAPI
from src.api import health_router, home_router

app = FastAPI()

# Register routers
app.include_router(home_router)
app.include_router(health_router)
```

## Template Placeholders

The home page HTML template uses the following placeholders:

- `${API_VERSION}` - Replaced with API version
- `${ENVIRONMENT}` - Replaced with environment name
- `${ENVIRONMENT_CLASS}` - Replaced with CSS class for environment badge

## TODO Items

1. Implement actual database health check in `health.py`
2. Connect to settings/config for version and environment
3. Add more comprehensive error handling
4. Add authentication if needed
5. Add rate limiting for public endpoints
