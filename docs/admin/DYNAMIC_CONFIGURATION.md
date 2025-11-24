# Dynamic Project Configuration

## Overview

The AKM system supports **dynamic runtime configuration** per project, allowing clients to update settings without code deployment or service restart. This enables self-service management of CORS, rate limits, IP restrictions, and other operational parameters.

## Architecture

### Configuration Layers

```
┌─────────────────────────────────────────────────────────────┐
│                   Configuration Priority                    │
├─────────────────────────────────────────────────────────────┤
│ 1. API Key Level      (Most Specific)                      │
│    └─ Individual key overrides                             │
│                                                             │
│ 2. Project Configuration (Database)                        │
│    └─ Runtime-configurable settings                        │
│                                                             │
│ 3. Global Defaults (Environment Variables)                 │
│    └─ Fallback values                                      │
└─────────────────────────────────────────────────────────────┘
```

## Supported Configurations

### 1. CORS Origins

**Purpose**: Control which domains can make requests to APIs protected by project keys.

**Storage**: `akm_project_configurations.cors_origins` (JSON array)

**Example**:
```json
{
  "cors_origins": [
    "https://app.example.com",
    "https://staging.example.com",
    "http://localhost:3000"
  ]
}
```

**Application**: 
- When a request is made with an API key, the system checks if the `Origin` header matches any configured origin
- If no project CORS is configured, falls back to global `CORS_ORIGINS` from env

### 2. Rate Limits

**Purpose**: Set default rate limits for all keys in a project.

**Storage**: Multiple columns in `akm_project_configurations`
- `default_rate_limit_per_minute`
- `default_rate_limit_per_hour`
- `default_rate_limit_per_day`
- `default_rate_limit_per_month`

**Priority**:
1. Individual key's rate limit (if set)
2. Project's default rate limit (if set)
3. Global default (from code)

**Example**:
```json
{
  "default_rate_limit_per_hour": 10000,
  "default_rate_limit_per_day": 200000
}
```

### 3. IP Allowlist

**Purpose**: Restrict API key usage to specific IP addresses or CIDR ranges.

**Storage**: `akm_project_configurations.ip_allowlist` (JSON array)

**Example**:
```json
{
  "ip_allowlist": [
    "203.0.113.0/24",
    "198.51.100.42",
    "192.0.2.0/25"
  ]
}
```

**Validation**:
- CIDR notation is validated on input
- Requests from non-allowlisted IPs are rejected with 403

### 4. Webhook Settings

**Purpose**: Configure webhook behavior per project.

**Storage**:
- `webhook_timeout_seconds` (default: 30)
- `webhook_max_retries` (default: 3)

**Example**:
```json
{
  "webhook_timeout_seconds": 60,
  "webhook_max_retries": 5
}
```

### 5. Custom Sensitive Fields

**Purpose**: Define project-specific fields that should be sanitized in logs.

**Storage**: `akm_project_configurations.custom_sensitive_fields` (JSON array)

**Example**:
```json
{
  "custom_sensitive_fields": [
    "customer_ssn",
    "credit_card",
    "internal_id"
  ]
}
```

**Integration**: Merged with global sensitive fields during sanitization.

## API Endpoints

### Create/Update Project Configuration

```http
PUT /akm/v1/projects/{project_id}/configuration
Content-Type: application/json
X-API-Key: akm_live_admin_key

{
  "cors_origins": ["https://app.example.com"],
  "default_rate_limit_per_hour": 5000,
  "ip_allowlist": ["203.0.113.0/24"],
  "webhook_timeout_seconds": 45,
  "custom_sensitive_fields": ["user_token"]
}
```

### Get Project Configuration

```http
GET /akm/v1/projects/{project_id}/configuration
X-API-Key: akm_live_admin_key
```

### Delete Configuration (Reset to Defaults)

```http
DELETE /akm/v1/projects/{project_id}/configuration
X-API-Key: akm_live_admin_key
```

## Configuration Application

### How Changes Are Applied

1. **No Restart Required**: Changes take effect immediately
2. **Database-Driven**: Configuration is read from DB on each request
3. **Caching**: Configurations are cached per request (not across requests)
4. **Fallback**: Missing configurations use global defaults

### Example Flow: CORS Check

```python
# Pseudo-code
def check_cors(request, api_key):
    # 1. Get project from API key
    project_id = api_key.project_id
    
    # 2. Load project configuration
    config = get_project_configuration(project_id)
    
    # 3. Check CORS
    if config.cors_origins:
        allowed = config.cors_origins
    else:
        allowed = settings.cors_origins_list  # Global fallback
    
    # 4. Validate origin
    if request.headers["Origin"] not in allowed:
        raise HTTPException(403, "CORS origin not allowed")
```

## Use Cases

### 1. Multi-Environment Development

**Scenario**: Client has dev, staging, and production environments.

**Solution**:
```json
{
  "cors_origins": [
    "http://localhost:3000",
    "https://dev.example.com",
    "https://staging.example.com",
    "https://example.com"
  ]
}
```

### 2. Gradual Rate Limit Increase

**Scenario**: Client starts with low limits, needs to scale up.

**Solution**: Update configuration without code changes
```json
{
  "default_rate_limit_per_hour": 50000  // Increased from 10000
}
```

### 3. Security Incident Response

**Scenario**: Suspicious activity detected from specific IPs.

**Solution**: Temporarily restrict to known IPs
```json
{
  "ip_allowlist": ["198.51.100.0/24"]  // Only corporate network
}
```

### 4. Compliance Requirements

**Scenario**: Client operates in regulated industry, needs custom field sanitization.

**Solution**:
```json
{
  "custom_sensitive_fields": [
    "patient_id",
    "medical_record_number",
    "ssn",
    "tax_id"
  ]
}
```

## Implementation Details

### Database Schema

```sql
CREATE TABLE akm_project_configurations (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL UNIQUE REFERENCES akm_projects(id) ON DELETE CASCADE,
    cors_origins JSONB,
    default_rate_limit_per_minute INTEGER,
    default_rate_limit_per_hour INTEGER,
    default_rate_limit_per_day INTEGER,
    default_rate_limit_per_month INTEGER,
    ip_allowlist JSONB,
    webhook_timeout_seconds INTEGER DEFAULT 30,
    webhook_max_retries INTEGER DEFAULT 3,
    custom_sensitive_fields JSONB,
    config_metadata JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_project_config_project ON akm_project_configurations(project_id);
```

### Repository Pattern

```python
class ProjectConfigurationRepository:
    async def get_by_project_id(project_id: int) -> Optional[AKMProjectConfiguration]
    async def upsert(project_id: int, config: dict) -> AKMProjectConfiguration
    async def delete(project_id: int) -> bool
```

### Validation Rules

1. **CORS Origins**: Must be valid URLs or wildcard patterns
2. **Rate Limits**: Must be positive integers
3. **IP Allowlist**: Must be valid IPv4/IPv6 addresses or CIDR notation
4. **Webhook Timeouts**: 1-300 seconds
5. **Webhook Retries**: 0-10 attempts

## Security Considerations

### Access Control

- Configuration management requires **project admin scope**: `akm:projects:write`
- Read access requires: `akm:projects:read`
- Configuration changes are **audited** in audit logs

### CORS Security

- Wildcard (`*`) is **not allowed** for security
- Each origin must be explicitly listed
- Origins are validated on configuration update

### IP Allowlist Security

- Empty allowlist means **no restrictions** (all IPs allowed)
- Non-empty allowlist is **enforced strictly**
- Invalid CIDR ranges are rejected

## Migration Guide

### Updating Client Applications

**Before (Hardcoded)**:
```javascript
const API_URL = "https://akm.example.com";
// Client is blocked by CORS
```

**After (Dynamic CORS)**:
```bash
# Admin updates configuration
curl -X PUT https://akm.example.com/akm/v1/projects/1/configuration \
  -H "X-API-Key: admin_key" \
  -H "Content-Type: application/json" \
  -d '{
    "cors_origins": ["https://client-app.com"]
  }'

# Client app now works immediately (no restart needed)
```

## Best Practices

### 1. Start Restrictive

Begin with minimal CORS origins and rate limits, expand as needed:
```json
{
  "cors_origins": ["https://production-only.com"],
  "default_rate_limit_per_hour": 1000
}
```

### 2. Use CIDR Ranges for IPs

Instead of individual IPs:
```json
{
  "ip_allowlist": ["203.0.113.0/24"]  // Entire subnet
}
```

### 3. Document Changes

Use `config_metadata` for change tracking:
```json
{
  "config_metadata": {
    "updated_by": "admin@example.com",
    "change_reason": "Added staging environment",
    "ticket": "OPS-1234"
  }
}
```

### 4. Test Before Production

Update staging project configuration first:
```bash
# Test on staging
PUT /akm/v1/projects/staging-project/configuration

# After validation, apply to production
PUT /akm/v1/projects/prod-project/configuration
```

## Monitoring

### Configuration Change Alerts

Set up alerts for configuration changes:
- CORS origins added/removed
- Rate limits significantly changed
- IP allowlist modified

### Audit Trail

All configuration changes are logged:
```json
{
  "event_type": "PROJECT_CONFIGURATION_UPDATED",
  "project_id": 123,
  "changes": {
    "cors_origins": ["https://new-domain.com"]
  },
  "updated_by_key_id": 456,
  "timestamp": "2025-11-23T22:00:00Z"
}
```

## Troubleshooting

### CORS Errors

**Symptom**: `Access-Control-Allow-Origin` errors in browser

**Solution**:
1. Check project configuration has correct origin
2. Ensure origin matches exactly (including protocol and port)
3. Verify API key belongs to correct project

### Rate Limit Exceeded

**Symptom**: 429 Too Many Requests

**Solution**:
1. Check current limits: `GET /akm/v1/projects/{id}/configuration`
2. Increase if justified: `PUT /akm/v1/projects/{id}/configuration`
3. Monitor usage to prevent abuse

### IP Blocked

**Symptom**: 403 Forbidden with "IP not allowed"

**Solution**:
1. Verify client IP address
2. Check allowlist includes IP/CIDR
3. Temporarily remove allowlist for testing

## Future Enhancements

- **Time-based rate limits**: Burst limits vs sustained
- **Geographic restrictions**: Allow/block by country
- **Custom headers**: Project-specific required headers
- **Automatic CORS detection**: Learn origins from usage patterns
- **Configuration versioning**: Rollback to previous configurations
- **A/B testing**: Split traffic with different rate limits

---

**Related Documentation**:
- [Multi-Tenant Architecture](ARCHITECTURE_ISSUES_AND_IMPROVEMENTS.md)
- [Rate Limiting](AKM_SYSTEM.md#rate-limiting)
- [Audit Logging](AUDIT_SYSTEM.md)
- [Sensitive Fields](SENSITIVE_FIELDS.md)
