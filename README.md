# API Key Management Service

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.121+-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A production-ready FastAPI application for secure API key management and authentication.

## 🚀 Features

### Core Capabilities

- **FastAPI Framework**: Modern, fast async web framework with automatic OpenAPI docs
- **Multi-Tenant Architecture**: Project-based isolation with prefix namespacing
- **Secure API Key Management**: SHA-256 hashed keys with PostgreSQL storage
- **RBAC with Scopes**: 30+ granular permissions with wildcard support (e.g., `akm:projects:*`)

### Advanced Security

- **Rate Limiting**: Per-minute, hourly, daily, and monthly limits per API key
- **IP Whitelisting**: CIDR-based IP restrictions per key configuration
- **Time Restrictions**: Configurable time windows for key usage
- **Audit Logging**: Cryptographic integrity with SHA-256 hashing and correlation IDs
- **Sensitive Data Sanitization**: Dynamic field-level redaction and masking

### Automation & Integration

- **Webhooks**: 15 event types with retry logic and HMAC-SHA256 signatures
- **Alert System**: Configurable alerts for rate limits, suspicious activity, and violations
- **OpenAPI Integration**: Automatic scope generation from OpenAPI specifications
- **Bulk Operations**: JSON-based bulk import for scopes and configurations

### Developer Experience

- **Database Migrations**: Alembic for version-controlled schema management
- **CLI Tools**: Comprehensive command-line utilities for database operations
- **Health Monitoring**: Kubernetes-ready liveness and readiness probes
- **Structured Logging**: BetterStack integration with correlation tracking
- **RESTful API**: Clean endpoints with comprehensive OpenAPI documentation
- **Usage Tracking**: Real-time monitoring of API key usage and request counts

## 📁 Project Structure

```
.
├── main.py                           # FastAPI application entry point
├── scripts/
│   ├── create_api_keys_table.py     # Initialize API keys table
│   └── manage_api_keys.py           # CLI for API key management
├── src/
│   ├── config.py                    # Configuration management
│   ├── logging_config.py            # Structured logging setup
│   ├── api/
│   │   ├── auth.py                  # API key authentication
│   │   └── routes/                  # API route handlers
│   └── database/
│       ├── connection.py            # Database connection
│       ├── models.py                # SQLAlchemy models
│       └── repositories/
│           └── api_key_repository.py # API key data access
├── alembic/                         # Database migrations
├── tests/                           # Unit and integration tests
└── docs/                            # Documentation
```

## 🛠️ Installation

### Prerequisites

- Python 3.12+
- PostgreSQL 13+
- pip or uv package manager

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd apikey_management
```

2. Create and activate virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

Required environment variables:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/apikeys
ENVIRONMENT=development
SECRET_KEY=your-secret-key-here
LOG_LEVEL=INFO
```

5. Run database migrations:
```bash
alembic upgrade head
```

## 🔑 API Key Management

### Create API Keys Table

First time setup - create the API keys table:
```bash
python scripts/create_api_keys_table.py
```

### Manage API Keys

The `manage_api_keys.py` script provides a full CLI for API key operations:

#### Create a new API key
```bash
python scripts/manage_api_keys.py create "My App" --description "Production API key"
```

With expiration (30 days):
```bash
python scripts/manage_api_keys.py create "Temp Key" --days 30
```

#### List all API keys
```bash
python scripts/manage_api_keys.py list
```

Include inactive keys:
```bash
python scripts/manage_api_keys.py list --include-inactive
```

#### Show key details
```bash
python scripts/manage_api_keys.py info 1
```

#### Revoke (deactivate) a key
```bash
python scripts/manage_api_keys.py revoke 1
```

#### Permanently delete a key
```bash
python scripts/manage_api_keys.py delete 1
```

## 🚀 Running the Application

### Development Server

```bash
uvicorn main:app --reload --port 8000
```

### Production Server

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Using Docker

```bash
docker build -t api-key-management .
docker run -p 8000:8000 --env-file .env api-key-management
```

## 📚 API Documentation

Once the server is running, access:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### User Guides (Web Interface)

- **[Quick Start Guide](https://your-domain.com/quickstart)** - Get started with AKM in minutes
- **[Administration Guide](https://your-domain.com/public/guides/admnistration.html)** - Admin deployment and management
- **[Authentication Guide](https://your-domain.com/authentication)** - Authentication patterns and security
- **[API Key Management](https://your-domain.com/api-key-management)** - Managing API keys and scopes
- **[API Versioning](https://your-domain.com/api-versioning)** - Version management strategies
- **[Deployment Guide](https://your-domain.com/deployment)** - Production deployment
- **[Testing Guide](https://your-domain.com/testing)** - Testing best practices

## 🔐 Authentication

All protected endpoints require the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key-here" http://localhost:8000/api/protected
```

### Authentication Flow

1. Client includes API key in `X-API-Key` header
2. Server validates key against database (SHA-256 hash)
3. Server checks if key is active and not expired
4. Server updates `last_used_at` and increments `request_count`
5. Request proceeds or returns 401 Unauthorized

## 🗃️ Database Schema

### API Keys Table

```sql
CREATE TABLE api_keys (
    id SERIAL PRIMARY KEY,
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE,
    last_used_at TIMESTAMP WITH TIME ZONE,
    request_count INTEGER DEFAULT 0
);
```

## 🧪 Testing

Run the test suite:

```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/unit/test_api_key_repository.py
```

## 📊 Monitoring & Logging

### Health Endpoints

- `GET /health` - Basic health check
- `GET /health/live` - Liveness probe (for Kubernetes)
- `GET /health/ready` - Readiness probe (checks database)

### Structured Logging

All logs include:
- Correlation IDs for request tracking
- Timestamp and log level
- Contextual information (API key name, request counts, etc.)
- Integration with BetterStack (Logtail) for production

### Metrics Tracked

- API key request counts
- Last used timestamps
- Authentication failures
- Request duration

## 🔧 Configuration

Key configuration options in `.env`:

```env
# Application
ENVIRONMENT=production
API_VERSION=1.0.0
HOST=0.0.0.0
PORT=8000

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Security
SECRET_KEY=your-secret-key
CORS_ORIGINS=http://localhost:3000,https://your-domain.com

# Logging
LOG_LEVEL=INFO
BETTERSTACK_SOURCE_TOKEN=your-token-here
```

## 🚀 Deployment

### Vercel

```bash
vercel deploy --prod
```

### AWS Lambda

Use Mangum adapter:
```python
from mangum import Mangum
handler = Mangum(app)
```

### Docker Compose

```bash
docker-compose up -d
```

## 📝 Migration Management

### Create a new migration

```bash
alembic revision --autogenerate -m "Add new field"
```

### Apply migrations

```bash
alembic upgrade head
```

### Rollback migration

```bash
alembic downgrade -1
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📚 Documentation

> **Note**: Interactive HTML versions of key guides are available through the web interface at `https://your-domain.com/` when the service is running.

### 🚀 Quick Start & Guides

- **[DEVELOPER_GUIDE.md](docs/DEVELOPER_GUIDE.md)** ⭐ - **Complete developer guide** with authentication, scopes, webhooks, configuration, alerts, and sensitive data
- **[AUTHENTICATION.md](docs/AUTHENTICATION.md)** - API authentication guide with security features and usage examples
- **[API_KEY_MANAGEMENT.md](docs/API_KEY_MANAGEMENT.md)** - Security best practices, key rotation, and incident response

### 📖 Feature Documentation

#### Scopes & Permissions

- **[SCOPES_BULK_INSERT.md](docs/SCOPES_BULK_INSERT.md)** - Bulk scope import with JSON/file upload and OpenAPI generation
- **[OPENAPI_SCOPE_GENERATION.md](docs/OPENAPI_SCOPE_GENERATION.md)** - Automatic scope generation from OpenAPI specifications
- **[BULK_SCOPES.md](docs/BULK_SCOPES.md)** - Bulk scope import system with JSON validation
- **[BULK_SCOPES_EXAMPLES.md](docs/BULK_SCOPES_EXAMPLES.md)** - Practical examples for bulk scope import

#### Webhooks & Events

- **[WEBHOOKS.md](docs/WEBHOOKS.md)** - Complete webhooks guide: registration, events, security, and delivery
- **[ALERTS.md](docs/ALERTS.md)** - Automated alerts for rate limits, security violations, and system events

#### Configuration Management

- **[CONFIGURATION_GUIDE.md](docs/CONFIGURATION_GUIDE.md)** - Project vs API Key configuration with priority hierarchy
- **[ENVIRONMENT.md](docs/ENVIRONMENT.md)** - Environment variables and configuration management

#### Data Protection & Audit

- **[SENSITIVE_FIELDS.md](docs/SENSITIVE_FIELDS.md)** - Dynamic sensitive field sanitization system with database configuration
- **[SENSITIVE_FIELDS_USAGE.md](docs/SENSITIVE_FIELDS_USAGE.md)** - Global vs project-specific sensitive fields usage guide
- **[SENSITIVE_FIELDS_IMPLEMENTATION_SUMMARY.md](docs/SENSITIVE_FIELDS_IMPLEMENTATION_SUMMARY.md)** - Sensitive fields implementation details
- **[AUDIT_SYSTEM.md](docs/AUDIT_SYSTEM.md)** - Complete audit logging with cryptographic integrity and correlation tracking
- **[AUDIT_IMPLEMENTATION_SUMMARY.md](docs/AUDIT_IMPLEMENTATION_SUMMARY.md)** - Audit system implementation details
- **[AUDIT_QUICK_START.md](docs/AUDIT_QUICK_START.md)** - Quick start guide for audit logging

### 🏗️ Architecture & Design

- **[AKM_SYSTEM.md](docs/AKM_SYSTEM.md)** - Complete AKM system overview with multi-tenancy, scopes, rate limiting, webhooks, and alerts
- **[ARCHITECTURE_ISSUES_AND_IMPROVEMENTS.md](docs/ARCHITECTURE_ISSUES_AND_IMPROVEMENTS.md)** - Multi-tenant architecture analysis and migration strategy
- **[MIGRATION.md](docs/MIGRATION.md)** - Database migration management with Alembic

### 🔧 Operations & Deployment

- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** - Vercel deployment guide with CI/CD configuration
- **[LOGGING.md](docs/LOGGING.md)** - Structured logging with BetterStack integration
- **[LOGGING_INSTRUMENTATION.md](docs/LOGGING_INSTRUMENTATION.md)** - Advanced logging instrumentation patterns
- **[TESTING.md](docs/TESTING.md)** - Testing guide with pytest, coverage, and CI/CD

### 🔐 GitHub Integration & CI/CD

- **[GITHUB_SECRETS_SETUP.md](docs/GITHUB_SECRETS_SETUP.md)** - GitHub secrets configuration for CI/CD
- **[GIT_ACTIONS_SECRETS_BESTPRACTICES.md](docs/GIT_ACTIONS_SECRETS_BESTPRACTICES.md)** - Security best practices for GitHub Actions

### 📝 Summaries & Examples

- **[AUTHENTICATION_SUMMARY.md](docs/AUTHENTICATION_SUMMARY.md)** - Authentication implementation summary
- **[REFACTORING_SUMMARY.md](docs/REFACTORING_SUMMARY.md)** - Project refactoring history and changes
- **[OPENAPI_EXAMPLES.md](docs/OPENAPI_EXAMPLES.md)** - Real-world OpenAPI scope generation examples

## 💡 Use Cases

### Enterprise Applications

- **Multi-Tenant SaaS**: Complete project isolation with prefix-based namespacing
- **Microservices Architecture**: Service-to-service authentication with scoped permissions
- **API Gateway**: Centralized API key management for distributed systems

### Security & Compliance

- **Audit Trail Requirements**: Cryptographic integrity with tamper-proof logging
- **PCI/SOC2 Compliance**: Sensitive data sanitization with customizable field rules
- **Access Control**: RBAC with 30+ granular scopes and wildcard support

### Developer Platforms

- **Third-Party Integrations**: Webhook-based event notifications with retry logic
- **Rate Limit Management**: Multi-tier limits (minute/hour/day/month) per API key
- **Self-Service Portals**: Bulk operations and OpenAPI-based scope generation

### IoT & Mobile

- **Device Authentication**: Secure device-to-server communication
- **Time-Based Access**: Configurable time windows for key usage
- **IP Restrictions**: CIDR-based IP whitelisting per device

## 🎯 Roadmap

- [x] **Multi-tenant support** - Project-based isolation implemented
- [x] **Scoped permissions** - RBAC with granular scopes
- [x] **Rate limiting** - Per-key and per-project limits
- [x] **Webhooks** - Event-driven notifications with retry
- [x] **Audit logging** - Cryptographic integrity tracking
- [x] **Sensitive fields** - Dynamic data sanitization
- [ ] Admin dashboard UI
- [ ] Key rotation automation
- [ ] IP whitelisting per key
- [ ] API usage analytics dashboard
- [ ] OAuth2/OIDC integration

## 📞 Support

For issues and questions:

- Open an issue on GitHub
- Check existing documentation in `/docs`
- Review API documentation at `/docs` endpoint

---

Built with ❤️ by Ideias Factory using FastAPI and Python
