# Logging Configuration with BetterStack

This document explains the advanced logging setup for the Brazilian CDS Data Feeder API with BetterStack (Logtail) integration.

## Overview

The application uses a sophisticated logging system that:

- **Structured JSON logging** in production for easy parsing and analysis
- **Human-readable logs** in development for debugging
- **Automatic BetterStack integration** in production environments
- **Request/response logging** with timing and context
- **Error tracking** with stack traces and context

## Configuration

### Environment Variables

Add these to your `.env` file:

```bash
# Logging Level
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# BetterStack Configuration (Production only)
BETTERSTACK_SOURCE_TOKEN=your_source_token_here
BETTERSTACK_INGESTING_HOST=in.logtail.com

# Environment (BetterStack only active in production)
ENVIRONMENT=production
```

### Vercel Environment Variables

In your Vercel project dashboard, add:

1. Go to **Settings** → **Environment Variables**
2. Add the following variables:

| Variable | Value | Environment |
|----------|-------|-------------|
| `BETTERSTACK_SOURCE_TOKEN` | Your BetterStack source token | Production |
| `BETTERSTACK_INGESTING_HOST` | `in.logtail.com` (or your custom host) | Production |
| `LOG_LEVEL` | `INFO` | All |
| `ENVIRONMENT` | `production` | Production |

**Note:** The `vercel.json` file includes placeholders using Vercel secrets (prefixed with `@`). You can set these up using:

```bash
vercel secrets add betterstack_source_token "your_token_here"
vercel secrets add betterstack_ingesting_host "in.logtail.com"
```

## Getting Your BetterStack Token

1. Sign up at [BetterStack](https://betterstack.com/logtail)
2. Create a new source for your application
3. Copy the **Source Token**
4. Use the ingesting host provided (usually `in.logtail.com`)

## Usage in Code

### Basic Logging

```python
from src.logging_config import get_logger

logger = get_logger(__name__)

# Simple logging
logger.info("Application started")
logger.warning("Potential issue detected")
logger.error("An error occurred")
```

### Logging with Context

```python
from src.logging_config import get_logger, log_with_context

logger = get_logger(__name__)

log_with_context(
    logger,
    'info',
    'User action completed',
    user_id='123',
    action='download',
    duration=1.5
)
```

### Request Logging Decorator

```python
from src.logging_config import log_request

@log_request
async def my_endpoint(request: Request):
    # Your code here
    return {"status": "success"}
```

This automatically logs:
- Request method and path
- Client IP address
- Request duration
- Response status
- Any errors that occur

## Log Format

### Development (Console)

```
2025-11-16 10:30:45 - brazilian_cds.main - INFO - Application started
```

### Production (JSON)

```json
{
  "timestamp": "2025-11-16T10:30:45.123Z",
  "level": "INFO",
  "name": "brazilian_cds.main",
  "message": "Application started",
  "environment": "production",
  "api_version": "2.0.0",
  "platform": "vercel",
  "context": {
    "user_id": "123",
    "action": "download"
  }
}
```

## Features

### 1. Automatic Request/Response Logging

All HTTP requests are automatically logged with:
- Method and path
- Client IP
- User agent
- Response status code
- Request duration

### 2. Structured Logging

All logs include:
- ISO 8601 timestamp
- Log level
- Environment (development/staging/production)
- API version
- Platform information (Vercel, local, etc.)

### 3. Error Tracking

Exceptions are automatically captured with:
- Full stack trace
- Exception type
- Error message
- Context at the time of error

### 4. Performance Monitoring

Request timing is automatically tracked and logged, helping identify slow endpoints.

## BetterStack Dashboard

Once configured, you can:

1. **Search and filter logs** by level, environment, or custom fields
2. **Set up alerts** for errors or specific conditions
3. **Create dashboards** to visualize metrics
4. **Track performance** over time
5. **Debug issues** with full context

## Best Practices

1. **Use appropriate log levels:**
   - `DEBUG`: Detailed diagnostic information
   - `INFO`: General informational messages
   - `WARNING`: Warning messages for potential issues
   - `ERROR`: Error messages for failures
   - `CRITICAL`: Critical failures requiring immediate attention

2. **Add context to logs:**
   ```python
   log_with_context(logger, 'info', 'Processing data', record_count=100, source='api')
   ```

3. **Don't log sensitive information:**
   - Passwords
   - API keys
   - Personal identifiable information (PII)
   - Credit card numbers

4. **Use structured logging in production:**
   The system automatically uses JSON format in production for better analysis.

## Troubleshooting

### Logs not appearing in BetterStack

1. Verify `ENVIRONMENT=production` (BetterStack only works in production)
2. Check your source token is correct
3. Ensure the ingesting host is reachable
4. Look for error messages in console output

### Too many logs

Adjust the `LOG_LEVEL` to reduce verbosity:
- `WARNING`: Only warnings and errors
- `ERROR`: Only errors and critical issues

### Missing context

Make sure you're using `log_with_context()` or the `@log_request` decorator to add context to your logs.

## Dependencies

The logging system requires:

- `python-json-logger`: For structured JSON logging
- `requests`: For sending logs to BetterStack

These are automatically installed via `requirements.txt`.
