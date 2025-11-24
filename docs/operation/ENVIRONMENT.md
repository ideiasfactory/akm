# Environment Configuration Guide

This guide explains how to configure environment variables for the Brazilian CDS Data Feeder API.

## Quick Start

1. **Development Setup**:
   ```bash
   # Copy the example file
   cp .env.example .env
   
   # Edit with your local settings
   nano .env
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application**:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## Environment Files

| File | Purpose | Version Control |
|------|---------|----------------|
| `.env.example` | Template with all available settings | ✅ Committed to repo |
| `.env` | Local development settings | ❌ Ignored by git |
| `.env.dev` | Development environment | ❌ Ignored by git |
| `.env.prod` | Production environment | ❌ Ignored by git |

## Configuration Structure

The application uses `pydantic-settings` to load and validate environment variables. All settings are defined in `src/config.py`.

### Application Settings

```bash
# Environment: development, staging, production
ENVIRONMENT=development

# API version displayed in docs and responses
API_VERSION=2.0.0

# Server configuration (local development only)
HOST=0.0.0.0
PORT=8000
```

### Database Configuration

```bash
# PostgreSQL connection string
DATABASE_URL=postgresql://user:password@localhost:5432/database_name

# Connection pool settings
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
```

**Format**: `postgresql://[user[:password]@][host][:port][/database]`

**Example**: `postgresql://admin:secret123@db.example.com:5432/cds_data`

### Security Settings

```bash
# Secret key for JWT tokens (generate with: openssl rand -hex 32)
SECRET_KEY=your-secret-key-here-change-in-production

# Token expiration in minutes
JWT_EXPIRATION_MINUTES=60

# CORS allowed origins (comma-separated)
CORS_ORIGINS=http://localhost:3000,http://localhost:8000
```

⚠️ **Important**: Always generate a unique `SECRET_KEY` for production:
```bash
openssl rand -hex 32
```

### Logging Configuration

```bash
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Optional log file path
LOG_FILE=/var/log/cds_datafeeder.log
```

### Feature Flags

```bash
# Enable/disable features
FEATURE_REALTIME_UPDATES=false
FEATURE_CACHING=true
FEATURE_RATE_LIMITING=true

# Rate limiting
RATE_LIMIT_PER_MINUTE=60
```

## Environment-Specific Configuration

### Development (.env or .env.dev)

```bash
ENVIRONMENT=development
LOG_LEVEL=DEBUG
FEATURE_RATE_LIMITING=false
DATABASE_URL=postgresql://localhost:5432/cds_datafeeder_dev
```

**Characteristics**:
- Debug logging enabled
- Rate limiting disabled for testing
- Local database
- Relaxed CORS settings

### Production (.env.prod)

```bash
ENVIRONMENT=production
LOG_LEVEL=INFO
FEATURE_RATE_LIMITING=true
DATABASE_URL=postgresql://user:password@prod-host:5432/cds_datafeeder_prod
SECRET_KEY=<generate-secure-key>
CORS_ORIGINS=https://your-production-domain.com
```

**Characteristics**:
- Info-level logging
- Rate limiting enabled
- Remote database
- Strict CORS settings
- Secure secret key

## Vercel Deployment

For Vercel deployments, set environment variables in the Vercel dashboard:

1. Go to your project settings
2. Navigate to "Environment Variables"
3. Add the following:

```
ENVIRONMENT=production
API_VERSION=2.0.0
DATABASE_URL=postgresql://...
SECRET_KEY=<secure-key>
CORS_ORIGINS=https://your-app.vercel.app
```

Vercel automatically sets `VERCEL=1` which the application uses to detect the platform.

## Using Settings in Code

Import and use the settings object:

```python
from src.config import settings

# Access configuration
print(f"Running in {settings.environment} mode")
print(f"API version: {settings.api_version}")

# Check environment
if settings.is_production:
    # Production-specific logic
    pass

# Use CORS origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list
)
```

## Validation

The `Settings` class validates all configuration on startup. If required variables are missing or invalid, the application will fail to start with a clear error message.

## Security Best Practices

1. **Never commit** `.env`, `.env.dev`, or `.env.prod` files
2. **Always generate** unique `SECRET_KEY` for each environment
3. **Use strong database passwords** with special characters
4. **Restrict CORS origins** in production
5. **Enable rate limiting** in production
6. **Use environment-specific** database credentials
7. **Rotate secrets** regularly

## Troubleshooting

### Settings not loading

```bash
# Check if .env file exists
ls -la .env

# Verify pydantic-settings is installed
pip list | grep pydantic-settings

# Check for syntax errors in .env
cat .env
```

### Import errors

```bash
# Install/reinstall dependencies
pip install -r requirements.txt

# Or specifically
pip install pydantic-settings python-dotenv
```

### Wrong environment detected

The application determines the environment in this order:
1. `ENVIRONMENT` environment variable
2. `VERCEL` environment variable (auto-sets to production)
3. Default: `development`

## Additional Resources

- [Pydantic Settings Documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
- [FastAPI Configuration Guide](https://fastapi.tiangolo.com/advanced/settings/)
- [Vercel Environment Variables](https://vercel.com/docs/concepts/projects/environment-variables)
