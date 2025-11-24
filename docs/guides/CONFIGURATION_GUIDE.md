# Configuration Management Guide

Understanding Project Configuration vs API Key Configuration in AKM.

## Overview

AKM supports **three-tier configuration hierarchy** with priority override:

```
1. API Key Configuration (Highest Priority) ⬆️
2. Project Configuration (Middle Priority) ⬆️
3. Global Defaults (Lowest Priority)
```

## Configuration Comparison

| Feature | Project Configuration | API Key Configuration |
|---------|----------------------|----------------------|
| **Endpoint** | `/projects/{id}/configuration` | `/projects/{id}/keys/{key_id}/config` |
| **Scope** | All keys in project | Single API key |
| **Priority** | Middle | Highest |
| **Use Case** | Team/environment defaults | Per-client customization |
| **Example** | Staging project CORS rules | VIP client higher limits |

---

## Project Configuration

Set defaults for **all API keys** in a project.

### Use Cases

- Environment-specific settings (dev/staging/prod)
- Team-wide policies
- Project defaults for new keys
- Organizational standards

### Create/Update

```bash
PUT /akm/v1/projects/{project_id}/configuration
Content-Type: application/json

{
  "cors_origins": [
    "https://app.example.com",
    "https://staging.example.com"
  ],
  "default_rate_limits": {
    "requests_per_minute": 1000,
    "requests_per_hour": 50000,
    "requests_per_day": 1000000,
    "requests_per_month": 30000000
  },
  "ip_allowlist": [
    "192.168.1.0/24",
    "10.0.0.0/8"
  ],
  "webhook_config": {
    "timeout_seconds": 30,
    "max_retries": 5
  },
  "sensitive_fields": ["password", "ssn", "credit_card"]
}
```

### Get Configuration

```bash
GET /akm/v1/projects/{project_id}/configuration
```

### Delete Configuration

```bash
DELETE /akm/v1/projects/{project_id}/configuration
```

Removes project configuration. Keys fall back to global defaults.

---

## API Key Configuration

Override project defaults for **specific API keys**.

### Use Cases

- VIP clients with higher limits
- Testing/development keys with relaxed rules
- Temporary access restrictions
- Client-specific security requirements

### Create/Update

```bash
PUT /akm/v1/projects/{project_id}/keys/{key_id}/config
Content-Type: application/json

{
  "rate_limits": {
    "requests_per_minute": 5000,
    "requests_per_hour": 200000,
    "requests_per_day": 5000000
  },
  "ip_restrictions": [
    "203.0.113.0/24"
  ],
  "allowed_methods": ["GET", "POST"],
  "allowed_endpoints": ["/api/users", "/api/products"],
  "time_restrictions": {
    "start_time": "08:00",
    "end_time": "18:00",
    "timezone": "America/New_York",
    "days_of_week": ["MON", "TUE", "WED", "THU", "FRI"]
  }
}
```

### Get Configuration

```bash
GET /akm/v1/projects/{project_id}/keys/{key_id}/config
```

### Get Effective Configuration

Get merged configuration after applying hierarchy:

```bash
GET /akm/v1/projects/{project_id}/keys/{key_id}/config/effective
```

Returns final configuration with all overrides applied.

---

## Configuration Priority Example

**Scenario:**

```yaml
Global Default:
  rate_limit: 100 req/min

Project Configuration (ID: 1):
  rate_limit: 500 req/min
  cors: ["https://app.example.com"]

API Key Configuration (ID: 42):
  rate_limit: 1000 req/min
```

**Result for Key 42:**
```yaml
rate_limit: 1000 req/min    # From key config (highest)
cors: ["https://app.example.com"]  # From project config
```

**Result for Key 43 (no key config):**
```yaml
rate_limit: 500 req/min     # From project config
cors: ["https://app.example.com"]  # From project config
```

---

## Configurable Settings

### Rate Limits

```json
{
  "rate_limits": {
    "requests_per_minute": 1000,
    "requests_per_hour": 50000,
    "requests_per_day": 1000000,
    "requests_per_month": 30000000
  }
}
```

### CORS Origins

```json
{
  "cors_origins": [
    "https://app.example.com",
    "https://admin.example.com",
    "*"
  ]
}
```

### IP Restrictions

```json
{
  "ip_allowlist": [
    "192.168.1.0/24",
    "10.0.0.0/8",
    "203.0.113.42"
  ]
}
```

### Allowed Methods

```json
{
  "allowed_methods": ["GET", "POST", "PUT"]
}
```

### Endpoint Restrictions

```json
{
  "allowed_endpoints": [
    "/api/users",
    "/api/products",
    "/api/orders"
  ]
}
```

### Time Restrictions

```json
{
  "time_restrictions": {
    "start_time": "09:00",
    "end_time": "17:00",
    "timezone": "America/New_York",
    "days_of_week": ["MON", "TUE", "WED", "THU", "FRI"]
  }
}
```

### Webhook Configuration

```json
{
  "webhook_config": {
    "timeout_seconds": 30,
    "max_retries": 5,
    "retry_backoff": "exponential"
  }
}
```

### Sensitive Fields

```json
{
  "sensitive_fields": [
    "password",
    "credit_card",
    "ssn",
    "api_key"
  ]
}
```

---

## Common Scenarios

### Scenario 1: Development Project

```bash
PUT /akm/v1/projects/1/configuration
{
  "cors_origins": ["*"],
  "default_rate_limits": {
    "requests_per_minute": 10000
  },
  "ip_allowlist": []
}
```

### Scenario 2: Production Project

```bash
PUT /akm/v1/projects/2/configuration
{
  "cors_origins": ["https://app.example.com"],
  "default_rate_limits": {
    "requests_per_minute": 1000
  },
  "ip_allowlist": ["203.0.113.0/24"]
}
```

### Scenario 3: VIP Client Key

```bash
PUT /akm/v1/projects/2/keys/42/config
{
  "rate_limits": {
    "requests_per_minute": 10000
  }
}
```

### Scenario 4: Testing Key

```bash
PUT /akm/v1/projects/2/keys/99/config
{
  "rate_limits": {
    "requests_per_minute": 100
  },
  "time_restrictions": {
    "start_time": "00:00",
    "end_time": "23:59"
  },
  "allowed_endpoints": ["/api/test"]
}
```

---

## Best Practices

### 1. Start with Project Defaults

Set sensible defaults at project level:

```bash
PUT /akm/v1/projects/1/configuration
{
  "default_rate_limits": {
    "requests_per_minute": 1000
  },
  "cors_origins": ["https://app.example.com"]
}
```

### 2. Override Only When Needed

Use key configuration sparingly:

```bash
# Only for exceptional cases
PUT /akm/v1/projects/1/keys/42/config
{
  "rate_limits": {
    "requests_per_minute": 5000
  }
}
```

### 3. Environment Separation

Different projects for environments:

- Project 1: Development (relaxed rules)
- Project 2: Staging (moderate rules)
- Project 3: Production (strict rules)

### 4. Document Overrides

When creating key-specific config, document reason:

```bash
PUT /akm/v1/projects/1/keys/42/config
{
  "rate_limits": {
    "requests_per_minute": 10000
  },
  "_comment": "VIP client - paid tier"
}
```

### 5. Regular Audits

Review configurations periodically:

```bash
# List all keys with custom config
GET /akm/v1/projects/1/keys?has_custom_config=true
```

---

## Configuration Changes

### Immediate Effect

Configuration changes apply **immediately** without restart:

1. Update configuration via API
2. Next request uses new configuration
3. No service interruption

### Audit Trail

All configuration changes are logged:

```bash
GET /akm/v1/audit/logs?resource=configuration&project_id=1
```

---

## Next Steps

- 📖 [Developer Guide](./DEVELOPER_GUIDE.md)
- 🚦 [Rate Limiting](./RATE_LIMITING.md)
- 🔔 [Alerts](./ALERTS.md)

---

**Tip:** Use `GET /config/effective` to debug which configuration is actually being applied.
