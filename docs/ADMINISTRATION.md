# 🔐 Administration Guide

Complete guide for administrators to deploy, configure, and manage the API Key Management Service.

## Table of Contents

- [Overview](#overview)
- [Initial Setup](#initial-setup)
- [Bootstrap Process](#bootstrap-process)
- [User Onboarding](#user-onboarding)
- [Project Management](#project-management)
- [Security Configuration](#security-configuration)
- [Monitoring & Audit](#monitoring--audit)
- [Backup & Recovery](#backup--recovery)
- [Maintenance Tasks](#maintenance-tasks)
- [Troubleshooting](#troubleshooting)

---

## Overview

As an administrator, you're responsible for:

- **Initial deployment** and configuration
- **Creating master credentials** for the bootstrap process
- **Onboarding new clients** by creating their projects and initial API keys
- **Monitoring system health** and usage patterns
- **Managing security policies** and access controls
- **Maintaining audit logs** for compliance
- **Performing backups** and disaster recovery

---

## Initial Setup

### Prerequisites

- **Python 3.10+** installed
- **PostgreSQL 14+** running
- **Git** for cloning the repository
- **Admin access** to the server/cloud environment
- **SSL certificates** for production (recommended)

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/ideiasfactory/apikey_management.git
cd apikey_management

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file with **secure production values**:

```env
# Database
DATABASE_URL=postgresql+asyncpg://apikey_user:STRONG_PASSWORD@localhost:5432/apikey_management

# Security
SECRET_KEY=generate-a-strong-random-secret-key-here-use-openssl-rand-hex-32
ADMIN_API_KEY=admin_master_key_change_this_immediately_after_bootstrap
ALGORITHM=HS256

# API Configuration
API_VERSION=1.0.0
ENVIRONMENT=production
CORS_ORIGINS=https://your-production-domain.com

# Rate Limiting
DEFAULT_RATE_LIMIT=1000
MAX_RATE_LIMIT=100000

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
AUDIT_RETENTION_DAYS=90

# Optional: External Services
WEBHOOK_TIMEOUT_SECONDS=30
EMAIL_NOTIFICATIONS_ENABLED=true
SMTP_HOST=smtp.your-email-provider.com
SMTP_PORT=587
SMTP_USER=notifications@your-domain.com
SMTP_PASSWORD=your-smtp-password
```

### 3. Generate Secure Keys

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate ADMIN_API_KEY
openssl rand -hex 32 | base64
```

### 4. Initialize Database

```bash
# Run Alembic migrations
alembic upgrade head

# Create initial tables
python scripts/create_api_keys_table.py

# Verify database
psql -d apikey_management -c "\dt"
```

### 5. Start the Service

```bash
# Production mode with multiple workers
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4 --log-config logging.json

# Or use systemd service (recommended)
sudo systemctl start apikey-management
sudo systemctl enable apikey-management
```

### 6. Verify Installation

```bash
# Health check
curl https://your-service.com/health

# Expected response
{
  "status": "healthy",
  "database": "connected",
  "version": "1.0.0",
  "timestamp": "2025-11-23T10:00:00Z"
}
```

---

## Bootstrap Process

The bootstrap process creates the initial administrative setup with just **2 simple steps**.

### Step 1: Create Admin Project

```bash
curl -X POST "https://your-service.com/akm/v1/projects" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ${ADMIN_API_KEY}" \
  -d '{
    "name": "system-admin",
    "description": "System administration project",
    "metadata": {
      "type": "admin",
      "created_by": "system"
    }
  }'
```

**Response:**

```json
{
  "id": "proj_admin_001",
  "name": "system-admin",
  "description": "System administration project",
  "created_at": "2025-11-23T10:00:00Z"
}
```

### Step 2: Generate Admin API Key

```bash
curl -X POST "https://your-service.com/akm/v1/keys" \
  -H "Content-Type: application/json" \
  -H "X-Admin-Key: ${ADMIN_API_KEY}" \
  -d '{
    "project_id": "proj_admin_001",
    "name": "primary-admin-key",
    "rate_limit": 100000,
    "expires_at": null
  }'
```

**Response:**

```json
{
  "id": "key_admin_001",
  "key": "akm_admin_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "name": "primary-admin-key",
  "rate_limit": 100000,
  "created_at": "2025-11-23T10:05:00Z"
}
```

⚠️ **CRITICAL**: Save this admin key securely! Store it in a password manager or secrets vault.

### Step 3: Project Admin Creates Scopes

Now the project administrator uses their API key to create necessary scopes:

```bash
# Full administrative access
curl -X POST "https://your-service.com/akm/v1/scopes" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: akm_admin_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6" \
  -d '{
    "name": "admin:full",
    "description": "Full administrative access",
    "project_id": "proj_admin_001"
  }'

# Project management
curl -X POST "https://your-service.com/akm/v1/scopes" \
  -H "X-API-Key: akm_admin_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "projects:manage",
    "description": "Create and manage projects",
    "project_id": "proj_admin_001"
  }'

# User management
curl -X POST "https://your-service.com/akm/v1/scopes" \
  -H "X-API-Key: akm_admin_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "users:manage",
    "description": "Manage user access",
    "project_id": "proj_admin_001"
  }'

# Audit log access
curl -X POST "https://your-service.com/akm/v1/scopes" \
  -H "X-API-Key: akm_admin_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "audit:read",
    "description": "Read audit logs",
    "project_id": "proj_admin_001"
  }'
```

### Step 4: Disable Bootstrap Mode

After creating the admin key, disable the `ADMIN_API_KEY` for security:

```bash
# Edit .env file
# Comment out or remove ADMIN_API_KEY
# ADMIN_API_KEY=  # Disabled after bootstrap

# Restart the service
sudo systemctl restart apikey-management
```

From now on, use the generated admin API key (`akm_admin_...`) for all administrative operations.

---

## User Onboarding

When a new client wants to use your service, follow this **2-step process**:

### Step 1: Create Client Project

```bash
curl -X POST "https://your-service.com/akm/v1/projects" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: akm_admin_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6" \
  -d '{
    "name": "client-acme-corp",
    "description": "ACME Corporation - Production Environment",
    "metadata": {
      "client_name": "ACME Corp",
      "client_email": "admin@acme.com",
      "tier": "enterprise",
      "onboarded_at": "2025-11-23T10:00:00Z"
    }
  }'
```

**Response:**

```json
{
  "id": "proj_client_acme_001",
  "name": "client-acme-corp",
  "description": "ACME Corporation - Production Environment",
  "created_at": "2025-11-23T10:00:00Z"
}
```

### Step 2: Generate Project Admin API Key

```bash
curl -X POST "https://your-service.com/akm/v1/keys" \
  -H "X-API-Key: akm_admin_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_client_acme_001",
    "name": "acme-project-admin-key",
    "rate_limit": 10000,
    "expires_at": "2026-11-23T23:59:59Z"
  }'
```

**Response:**

```json
{
  "id": "key_acme_admin_001",
  "key": "akm_live_x9y8z7w6v5u4t3s2r1q0p9o8n7m6l5k4",
  "name": "acme-project-admin-key",
  "rate_limit": 10000,
  "created_at": "2025-11-23T10:15:00Z",
  "expires_at": "2026-11-23T23:59:59Z"
}
```

### Step 3: Client Manages Their Own Scopes

Once the client receives their project admin API key, **they can manage their own scopes**:

#### Create Scopes

```bash
# Client creates their own scopes
curl -X POST "https://your-service.com/akm/v1/scopes" \
  -H "X-API-Key: akm_live_x9y8z7w6v5u4t3s2r1q0p9o8n7m6l5k4" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "users:read",
    "description": "Read user data",
    "project_id": "proj_client_acme_001"
  }'
```

#### Import OpenAPI Spec (Optional)

Client can import their own OpenAPI/Swagger spec:

```bash
curl -X POST "https://your-service.com/akm/v1/import/openapi" \
  -H "X-API-Key: akm_live_x9y8z7w6v5u4t3s2r1q0p9o8n7m6l5k4" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_client_acme_001",
    "spec_url": "https://acme-api.com/openapi.json",
    "auto_create_scopes": true,
    "scope_prefix": "acme"
  }'
```

This automatically creates scopes based on their API operations.

#### Generate Additional Keys

Client can create additional API keys with specific scopes:

```bash
curl -X POST "https://your-service.com/akm/v1/keys" \
  -H "X-API-Key: akm_live_x9y8z7w6v5u4t3s2r1q0p9o8n7m6l5k4" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_client_acme_001",
    "name": "acme-production-key",
    "scopes": ["users:read", "users:write", "orders:read", "orders:write"],
    "rate_limit": 5000,
    "expires_at": "2026-11-23T23:59:59Z"
  }'
```

### Step 4: Provide Credentials to Client

Send the client their credentials securely:

**Email Template:**

```
Subject: Your API Key Management Service Credentials

Hello ACME Corp Team,

Your API Key Management Service account is now active!

Project ID: proj_client_acme_001
Project Admin API Key: akm_live_x9y8z7w6v5u4t3s2r1q0p9o8n7m6l5k4
Rate Limit: 10,000 requests/hour
Expires: 2026-11-23

What You Can Do Now:
✅ Create and manage your own scopes
✅ Import your OpenAPI/Swagger spec to auto-generate scopes
✅ Generate additional API keys with specific permissions
✅ Monitor usage and manage your keys

Quick Start Guide: https://your-service.com/quickstart
API Documentation: https://your-service.com/docs

Important Security Notes:
- Store this API key securely (use environment variables)
- Never commit keys to version control
- Rotate keys every 90 days for security
- You can generate additional keys yourself

Support: support@your-service.com
```

---

## Project Management

### List All Projects

```bash
curl -X GET "https://your-service.com/akm/v1/projects" \
  -H "X-API-Key: akm_admin_..."
```

### Update Project

```bash
curl -X PUT "https://your-service.com/akm/v1/projects/proj_client_acme_001" \
  -H "X-API-Key: akm_admin_..." \
  -H "Content-Type: application/json" \
  -d '{
    "description": "ACME Corporation - Production & Staging",
    "metadata": {
      "tier": "enterprise-plus",
      "upgraded_at": "2025-11-23T15:00:00Z"
    }
  }'
```

### Suspend Project

```bash
curl -X POST "https://your-service.com/akm/v1/projects/proj_client_acme_001/suspend" \
  -H "X-API-Key: akm_admin_..." \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Payment overdue",
    "notify_client": true
  }'
```

### Delete Project

⚠️ **Warning**: This permanently deletes all keys and data!

```bash
curl -X DELETE "https://your-service.com/akm/v1/projects/proj_client_acme_001" \
  -H "X-API-Key: akm_admin_..." \
  -H "X-Confirm-Delete: yes"
```

---

## Security Configuration

### Rate Limit Policies

Define rate limit tiers:

```python
# config/rate_limits.py
RATE_LIMIT_TIERS = {
    "free": 100,        # 100 requests/hour
    "starter": 1000,    # 1K requests/hour
    "professional": 10000,   # 10K requests/hour
    "enterprise": 100000,    # 100K requests/hour
    "unlimited": None        # No limit
}
```

### Key Expiration Policies

```python
# config/security.py
KEY_EXPIRATION_POLICIES = {
    "development": 90,    # 90 days
    "staging": 180,       # 180 days
    "production": 365,    # 1 year
    "permanent": None     # No expiration
}
```

### IP Allowlisting

Configure IP restrictions for sensitive projects:

```bash
curl -X POST "https://your-service.com/akm/v1/projects/proj_client_acme_001/ip-allowlist" \
  -H "X-API-Key: akm_admin_..." \
  -H "Content-Type: application/json" \
  -d '{
    "allowed_ips": [
      "203.0.113.0/24",
      "198.51.100.50"
    ],
    "description": "ACME production servers"
  }'
```

### Webhook Configuration

Set up webhooks for security events:

```bash
curl -X POST "https://your-service.com/akm/v1/webhooks" \
  -H "X-API-Key: akm_admin_..." \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "system-admin",
    "url": "https://admin-alerts.your-service.com/webhooks",
    "events": [
      "key.created",
      "key.revoked",
      "key.expired",
      "rate_limit.exceeded",
      "suspicious_activity.detected"
    ],
    "secret": "webhook_secret_for_validation"
  }'
```

---

## Monitoring & Audit

### View System Statistics

```bash
curl -X GET "https://your-service.com/akm/v1/admin/stats" \
  -H "X-API-Key: akm_admin_..."
```

**Response:**

```json
{
  "total_projects": 42,
  "total_keys": 156,
  "active_keys": 142,
  "expired_keys": 14,
  "total_requests_today": 1234567,
  "rate_limit_hits_today": 89,
  "top_projects_by_usage": [
    {"project_id": "proj_client_acme_001", "requests": 450000},
    {"project_id": "proj_client_widgets_002", "requests": 320000}
  ]
}
```

### Query Audit Logs

```bash
# All events from last 24 hours
curl -X GET "https://your-service.com/akm/v1/audit-logs?since=24h" \
  -H "X-API-Key: akm_admin_..."

# Specific project
curl -X GET "https://your-service.com/akm/v1/audit-logs?project_id=proj_client_acme_001&limit=100" \
  -H "X-API-Key: akm_admin_..."

# Specific event types
curl -X GET "https://your-service.com/akm/v1/audit-logs?event_types=key.created,key.revoked" \
  -H "X-API-Key: akm_admin_..."
```

### Export Audit Logs

```bash
# Export to CSV
curl -X GET "https://your-service.com/akm/v1/audit-logs/export?format=csv&start=2025-11-01&end=2025-11-30" \
  -H "X-API-Key: akm_admin_..." \
  -o audit_logs_november_2025.csv

# Export to JSON
curl -X GET "https://your-service.com/akm/v1/audit-logs/export?format=json&start=2025-11-01&end=2025-11-30" \
  -H "X-API-Key: akm_admin_..." \
  -o audit_logs_november_2025.json
```

### Set Up Monitoring Alerts

```python
# scripts/monitoring_alerts.py
import httpx
import asyncio

async def check_health():
    async with httpx.AsyncClient() as client:
        response = await client.get("https://your-service.com/health")
        if response.status_code != 200:
            await send_alert("Health check failed!")

async def check_rate_limits():
    # Query keys approaching rate limits
    pass

# Run every 5 minutes
asyncio.run(check_health())
```

---

## Backup & Recovery

### Database Backup

```bash
# Daily backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/apikey_management"

# Create backup
pg_dump -U apikey_user -d apikey_management \
  -F c -f "${BACKUP_DIR}/backup_${DATE}.dump"

# Compress
gzip "${BACKUP_DIR}/backup_${DATE}.dump"

# Keep only last 30 days
find ${BACKUP_DIR} -name "backup_*.dump.gz" -mtime +30 -delete

# Upload to S3 (optional)
aws s3 cp "${BACKUP_DIR}/backup_${DATE}.dump.gz" \
  s3://your-backup-bucket/apikey-management/
```

### Restore from Backup

```bash
# Stop the service
sudo systemctl stop apikey-management

# Restore database
gunzip -c backup_20251123_100000.dump.gz | pg_restore -U apikey_user -d apikey_management

# Start the service
sudo systemctl start apikey-management
```

### Export/Import Projects

```bash
# Export single project
curl -X GET "https://your-service.com/akm/v1/projects/proj_client_acme_001/export" \
  -H "X-API-Key: akm_admin_..." \
  -o acme_project_export.json

# Import project
curl -X POST "https://your-service.com/akm/v1/projects/import" \
  -H "X-API-Key: akm_admin_..." \
  -H "Content-Type: application/json" \
  -d @acme_project_export.json
```

---

## Maintenance Tasks

### Rotate Admin Keys

Every 90 days, rotate admin keys:

```bash
# 1. Generate new admin key
curl -X POST "https://your-service.com/akm/v1/keys" \
  -H "X-API-Key: akm_admin_OLD..." \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_admin_001",
    "name": "primary-admin-key-2025-Q4",
    "scopes": ["admin:full", "projects:manage", "users:manage", "audit:read"],
    "rate_limit": 100000
  }'

# 2. Update your scripts/configs with new key

# 3. Revoke old key
curl -X DELETE "https://your-service.com/akm/v1/keys/key_admin_001" \
  -H "X-API-Key: akm_admin_NEW..."
```

### Clean Expired Keys

```bash
# Automated cleanup script
curl -X POST "https://your-service.com/akm/v1/admin/cleanup/expired-keys" \
  -H "X-API-Key: akm_admin_..."
```

### Purge Old Audit Logs

```bash
# Delete logs older than retention period
curl -X POST "https://your-service.com/akm/v1/admin/cleanup/audit-logs" \
  -H "X-API-Key: akm_admin_..." \
  -H "Content-Type: application/json" \
  -d '{
    "older_than_days": 90,
    "dry_run": false
  }'
```

### Update Rate Limits

```bash
# Bulk update for tier upgrade
curl -X POST "https://your-service.com/akm/v1/admin/bulk-update-rate-limits" \
  -H "X-API-Key: akm_admin_..." \
  -H "Content-Type: application/json" \
  -d '{
    "project_ids": ["proj_client_acme_001", "proj_client_widgets_002"],
    "new_rate_limit": 50000
  }'
```

---

## Troubleshooting

### Issue: Client Can't Authenticate

**Symptoms**: `401 Unauthorized` errors

**Diagnosis**:

```bash
# Check if key exists and is active
curl -X GET "https://your-service.com/akm/v1/keys/key_acme_prod_001" \
  -H "X-API-Key: akm_admin_..."

# Check audit logs for failed attempts
curl -X GET "https://your-service.com/akm/v1/audit-logs?event_type=auth.failed&project_id=proj_client_acme_001" \
  -H "X-API-Key: akm_admin_..."
```

**Solutions**:
- Verify key hasn't expired
- Check if project is suspended
- Ensure key has required scopes
- Regenerate key if compromised

### Issue: High Rate Limit Hits

**Symptoms**: Many `429 Too Many Requests` errors

**Diagnosis**:

```bash
# Check rate limit statistics
curl -X GET "https://your-service.com/akm/v1/admin/rate-limit-stats?project_id=proj_client_acme_001" \
  -H "X-API-Key: akm_admin_..."
```

**Solutions**:
- Increase rate limit for legitimate clients
- Identify and block abusive patterns
- Contact client about optimization

### Issue: Database Connection Failures

**Symptoms**: `500 Internal Server Error`, health check fails

**Diagnosis**:

```bash
# Check database status
systemctl status postgresql

# Check connections
psql -d apikey_management -c "SELECT count(*) FROM pg_stat_activity;"

# Check logs
tail -f /var/log/apikey-management/app.log
```

**Solutions**:
- Restart PostgreSQL if needed
- Increase connection pool size
- Check for long-running queries

### Issue: Webhook Delivery Failures

**Symptoms**: Webhooks not received by clients

**Diagnosis**:

```bash
# Check webhook logs
curl -X GET "https://your-service.com/akm/v1/admin/webhook-logs?status=failed" \
  -H "X-API-Key: akm_admin_..."
```

**Solutions**:
- Verify client webhook endpoint is accessible
- Check webhook signature validation
- Retry failed deliveries
- Update webhook URL if changed

---

## CLI Administration Tool

For convenience, use the admin CLI:

```bash
# Install CLI
pip install akm-admin-cli

# Configure
akm-admin configure --api-key akm_admin_... --base-url https://your-service.com/akm

# Common commands
akm-admin projects list
akm-admin projects create --name "client-name"
akm-admin keys generate --project proj_xxx --scopes "users:read,users:write"
akm-admin keys list --project proj_xxx
akm-admin keys revoke --key-id key_xxx
akm-admin audit query --since 24h
akm-admin stats show
```

---

## Additional Resources

- [Quick Start Guide](/quickstart) - Client integration guide
- [API Versioning](/api-versioning) - Version management
- [Deployment Guide](/deployment) - Production deployment
- [Testing Guide](/testing) - Running tests
- [API Reference](/docs) - Interactive documentation

---

**Need Help?** Contact the development team or check the [GitHub Issues](https://github.com/ideiasfactory/apikey_management/issues).
