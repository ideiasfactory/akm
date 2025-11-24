# Developer Guide - API Key Management Service

Complete guide for developers integrating with the AKM API.

## Table of Contents

- [Authentication](#authentication)
- [Scopes & Permissions](#scopes--permissions)
- [Webhooks](#webhooks)
- [Configuration Management](#configuration-management)
- [Alerts](#alerts)
- [Sensitive Data](#sensitive-data)
- [Rate Limits](#rate-limits)

---

## Authentication

All API requests require authentication using an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: akm_your_key_here" https://api.example.com/akm/v1/projects
```

### Getting Your First API Key

Use the management CLI to create your first API key:

```bash
python scripts/manage_api_keys.py create \
  --project-id 1 \
  --scopes "akm:*" \
  --description "Admin key"
```

📖 **See also:** [Authentication Guide](./AUTHENTICATION.md)

---

## Scopes & Permissions

Scopes define what actions an API key can perform. AKM uses hierarchical RBAC with wildcard support.

### Scope Format

```
akm:resource:action
```

Examples:
- `akm:projects:read` - Read projects
- `akm:keys:*` - All key operations
- `akm:*` - Admin access (all operations)

### Managing Scopes

#### Create a Scope

```bash
POST /akm/v1/projects/{project_id}/scopes
Content-Type: application/json

{
  "scope_name": "akm:users:read",
  "description": "Read user data",
  "resource_type": "users",
  "action": "read"
}
```

#### List Scopes

```bash
GET /akm/v1/projects/{project_id}/scopes
```

### Bulk Operations

Create multiple scopes at once using the bulk endpoint:

```bash
POST /akm/v1/projects/{project_id}/scopes/bulk
Content-Type: application/json

{
  "scopes": [
    {
      "scope_name": "akm:users:read",
      "description": "Read user data",
      "resource_type": "users",
      "action": "read"
    },
    {
      "scope_name": "akm:users:write",
      "description": "Create and update users",
      "resource_type": "users",
      "action": "write"
    }
  ]
}
```

**Response:**
```json
{
  "total_processed": 2,
  "created": 2,
  "updated": 0,
  "skipped": 0,
  "errors": [],
  "scope_names": ["akm:users:read", "akm:users:write"]
}
```

### Generate from OpenAPI Specification

Automatically generate scopes from your OpenAPI/Swagger spec:

```bash
POST /akm/v1/openapi-scopes/generate/{project_id}
Content-Type: application/json

{
  "openapi_url": "https://api.example.com/openapi.json",
  "prefix": "akm",
  "auto_apply": false
}
```

This analyzes your OpenAPI spec and suggests scopes based on:
- HTTP methods (GET → read, POST/PUT → write, DELETE → delete)
- Endpoint paths (extract resource names)
- Operation IDs and tags

**Example output:**
```json
{
  "project_id": 1,
  "total_generated": 15,
  "scopes": [
    {
      "scope_name": "akm:users:read",
      "description": "Read user data",
      "resource_type": "users",
      "action": "read",
      "endpoints": ["/users", "/users/{id}"]
    }
  ],
  "applied": false
}
```

Set `auto_apply: true` to automatically create the scopes.

📖 **See also:** [Scopes Bulk Insert Guide](./SCOPES_BULK_INSERT.md)

---

## Webhooks

Webhooks allow you to receive real-time notifications about events in your AKM instance.

### Webhook Flow

1. **Register webhook URL** for your API key
2. **Subscribe to events** you want to receive
3. **Receive POST requests** when events occur
4. **Verify HMAC signature** for security

### Creating a Webhook

```bash
POST /akm/v1/projects/{project_id}/keys/{key_id}/webhooks
Content-Type: application/json

{
  "url": "https://your-app.com/webhooks/akm",
  "secret": "your-webhook-secret-key",
  "enabled": true,
  "events": ["api_key.created", "api_key.revoked"],
  "description": "Production webhook"
}
```

### Subscribing to Events

```bash
PUT /akm/v1/projects/{project_id}/keys/{key_id}/webhooks/{webhook_id}/subscriptions/{event_type}
```

### Available Events

| Event Type | Description | Payload |
|-----------|-------------|---------|
| `api_key.created` | New API key created | Key ID, project ID, scopes |
| `api_key.updated` | API key modified | Key ID, changed fields |
| `api_key.revoked` | API key revoked | Key ID, revocation reason |
| `api_key.expired` | API key expired | Key ID, expiration date |
| `rate_limit.exceeded` | Rate limit hit | Key ID, limit type, current count |
| `rate_limit.warning` | Approaching limit (80%) | Key ID, limit type, percentage |
| `ip_restriction.violated` | Request from unauthorized IP | Key ID, IP address, CIDR rules |
| `scope.violation` | Insufficient permissions | Key ID, required scope, attempted action |
| `alert.triggered` | Alert rule triggered | Alert ID, rule type, details |
| `webhook.delivery.failed` | Webhook delivery failed | Webhook ID, error, retry count |
| `audit.integrity.violation` | Audit log tampered | Log ID, expected hash, actual hash |
| `project.created` | New project created | Project ID, name |
| `project.updated` | Project modified | Project ID, changed fields |
| `project.deleted` | Project deleted | Project ID |
| `config.updated` | Configuration changed | Config type, old/new values |

### Webhook Payload Format

All webhooks use a consistent format:

```json
{
  "event_id": "evt_1a2b3c4d5e6f",
  "event_type": "api_key.created",
  "timestamp": "2025-11-23T21:00:00Z",
  "api_key_id": 42,
  "project_id": 1,
  "data": {
    "key_id": 42,
    "scopes": ["akm:users:read"],
    "created_by": "admin@example.com"
  },
  "correlation_id": "req_abc123"
}
```

### Verifying Webhook Signatures

Every webhook includes an HMAC-SHA256 signature in the `X-Webhook-Signature` header:

```python
import hmac
import hashlib

def verify_webhook(payload_body: bytes, signature: str, secret: str) -> bool:
    """Verify webhook signature"""
    expected = hmac.new(
        secret.encode(),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)

# Usage in your webhook handler
@app.post("/webhooks/akm")
async def handle_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature")
    
    if not verify_webhook(body, signature, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    payload = await request.json()
    # Process webhook...
```

### Retry Policy

Failed webhook deliveries are automatically retried:

- **Retry attempts:** 5
- **Backoff:** Exponential (1s, 2s, 4s, 8s, 16s)
- **Timeout:** 30 seconds per attempt
- **Failure event:** `webhook.delivery.failed` after all retries exhausted

### Testing Webhooks

Use the webhook test endpoint:

```bash
POST /akm/v1/projects/{project_id}/keys/{key_id}/webhooks/{webhook_id}/test
```

This sends a test event to verify your webhook endpoint is working.

📖 **See also:** [Webhooks Documentation](./WEBHOOKS.md)

---

## Configuration Management

AKM supports three levels of configuration with priority override:

1. **API Key Configuration** (highest priority)
2. **Project Configuration** (middle priority)
3. **Global Defaults** (lowest priority)

### API Key Configuration vs Project Configuration

| Feature | API Key Configuration | Project Configuration |
|---------|----------------------|----------------------|
| **Scope** | Single API key | All keys in project |
| **Use Case** | Per-client customization | Project-wide defaults |
| **Priority** | Highest (overrides project) | Middle (overrides global) |
| **Example** | VIP client gets higher limits | Staging project has relaxed CORS |
| **Endpoint** | `/projects/{id}/keys/{key_id}/config` | `/projects/{id}/configuration` |

### Project Configuration

Set project-wide defaults:

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

**When to use:**
- Setting defaults for all API keys in a project
- Environment-specific configuration (dev/staging/prod)
- Team-wide policies

### API Key Configuration

Override project defaults for specific keys:

```bash
PUT /akm/v1/projects/{project_id}/keys/{key_id}/config
Content-Type: application/json

{
  "rate_limits": {
    "requests_per_minute": 5000,
    "requests_per_hour": 200000
  },
  "ip_restrictions": [
    "203.0.113.0/24"
  ],
  "allowed_methods": ["GET", "POST"],
  "time_restrictions": {
    "start_time": "08:00",
    "end_time": "18:00",
    "timezone": "America/New_York"
  }
}
```

**When to use:**
- VIP clients need higher rate limits
- Specific security requirements for a client
- Temporary access restrictions
- Testing scenarios

### Configuration Priority Example

Given:
- **Global default:** 100 req/min
- **Project config:** 500 req/min
- **Key config:** 1000 req/min

Result: API key gets **1000 req/min** (highest priority)

If key config is removed: API key falls back to **500 req/min** (project default)

### Getting Effective Configuration

```bash
GET /akm/v1/projects/{project_id}/keys/{key_id}/config/effective
```

Returns the merged configuration after applying priority rules.

---

## Alerts

Set up automated alerts for important events.

### Alert Types

| Type | Trigger | Use Case |
|------|---------|----------|
| `RATE_LIMIT_THRESHOLD` | Approaching rate limit | Prevent service disruption |
| `SUSPICIOUS_ACTIVITY` | Unusual patterns detected | Security monitoring |
| `IP_VIOLATION` | Unauthorized IP access | Security alerts |
| `SCOPE_VIOLATION` | Permission denied | Access control auditing |
| `EXPIRY_WARNING` | Key expiring soon | Renewal reminders |
| `USAGE_ANOMALY` | Unusual usage pattern | Fraud detection |

### Creating an Alert

```bash
POST /akm/v1/projects/{project_id}/keys/{key_id}/alerts
Content-Type: application/json

{
  "alert_type": "RATE_LIMIT_THRESHOLD",
  "threshold": 80,
  "enabled": true,
  "notification_channels": ["webhook", "email"],
  "webhook_url": "https://your-app.com/alerts",
  "email_recipients": ["ops@example.com"],
  "cooldown_minutes": 30
}
```

### Alert Payload

When an alert triggers, you receive:

```json
{
  "alert_id": 123,
  "alert_type": "RATE_LIMIT_THRESHOLD",
  "api_key_id": 42,
  "project_id": 1,
  "triggered_at": "2025-11-23T21:30:00Z",
  "details": {
    "current_usage": 850,
    "limit": 1000,
    "percentage": 85.0,
    "window": "per_hour"
  },
  "severity": "warning"
}
```

### Alert History

```bash
GET /akm/v1/alerts/history?key_id=42&days=7
```

### Alert Statistics

```bash
GET /akm/v1/alerts/stats?project_id=1
```

Returns aggregated metrics:
- Total alerts by type
- Most triggered alerts
- Average response time
- Alert trends

---

## Sensitive Data

Protect sensitive information in logs and webhook payloads.

### How It Works

1. Define sensitive field patterns
2. AKM automatically sanitizes matching fields in:
   - Audit logs
   - Webhook payloads
   - Error responses
   - Debug output

### Defining Sensitive Fields

#### Global Fields (all projects)

```bash
POST /akm/v1/sensitive-fields
Content-Type: application/json

{
  "field_pattern": "password",
  "redaction_type": "MASK",
  "mask_character": "*",
  "show_last_chars": 0,
  "enabled": true
}
```

#### Project-Specific Fields

```bash
POST /akm/v1/projects/{project_id}/sensitive-fields
Content-Type: application/json

{
  "field_pattern": "api_key",
  "redaction_type": "PARTIAL",
  "mask_character": "*",
  "show_last_chars": 4,
  "enabled": true
}
```

### Redaction Types

| Type | Example Input | Example Output | Use Case |
|------|--------------|----------------|----------|
| `MASK` | `secret123` | `**********` | Passwords, tokens |
| `PARTIAL` | `secret123` | `******t123` | API keys, IDs |
| `HASH` | `secret123` | `a665a45...` | Pseudonymization |
| `REMOVE` | `secret123` | `[REDACTED]` | Complete removal |

### Field Pattern Matching

Supports multiple patterns:

```json
{
  "field_pattern": "password|secret|token|api_key"
}
```

Matches:
- `user_password`
- `client_secret`
- `access_token`
- `api_key_hash`

### Example: Before and After

**Before sanitization:**
```json
{
  "username": "john_doe",
  "password": "SuperSecret123!",
  "api_key": "akm_1234567890abcdef",
  "email": "john@example.com"
}
```

**After sanitization:**
```json
{
  "username": "john_doe",
  "password": "**********",
  "api_key": "akm_**********cdef",
  "email": "john@example.com"
}
```

---

## Rate Limits

AKM enforces multiple time windows for rate limiting.

### Rate Limit Windows

- **Per minute:** Burst protection
- **Per hour:** Short-term limiting
- **Per day:** Daily quotas
- **Per month:** Billing periods

### Checking Rate Limits

Rate limit information is returned in response headers:

```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 847
X-RateLimit-Reset: 1732396800
X-RateLimit-Window: per_minute
```

### Rate Limit Response

When limit is exceeded:

```http
HTTP/1.1 429 Too Many Requests
Content-Type: application/json
Retry-After: 42

{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded for per_minute window",
  "limit": 1000,
  "window": "per_minute",
  "retry_after": 42,
  "correlation_id": "req_abc123"
}
```

### Best Practices

1. **Implement exponential backoff**
2. **Monitor X-RateLimit-Remaining header**
3. **Set up alerts at 80% threshold**
4. **Cache responses when possible**
5. **Use webhooks instead of polling**

### Example: Handling Rate Limits

```python
import time
import requests

def api_call_with_retry(url, headers, max_retries=3):
    """Make API call with automatic retry on rate limit"""
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Waiting {retry_after}s...")
            time.sleep(retry_after)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

---

## Quick Reference

### Common Operations

```bash
# Create API key
POST /akm/v1/projects/{project_id}/keys

# List keys
GET /akm/v1/projects/{project_id}/keys

# Revoke key
POST /akm/v1/projects/{project_id}/keys/{key_id}/revoke

# Create scope
POST /akm/v1/projects/{project_id}/scopes

# Bulk import scopes
POST /akm/v1/projects/{project_id}/scopes/bulk

# Register webhook
POST /akm/v1/projects/{project_id}/keys/{key_id}/webhooks

# Subscribe to event
PUT /akm/v1/projects/{project_id}/keys/{key_id}/webhooks/{webhook_id}/subscriptions/{event_type}

# Create alert
POST /akm/v1/projects/{project_id}/keys/{key_id}/alerts

# Configure project
PUT /akm/v1/projects/{project_id}/configuration

# Configure key
PUT /akm/v1/projects/{project_id}/keys/{key_id}/config
```

### Authentication Header

```bash
X-API-Key: akm_your_key_here
```

### Base URLs

- **v1 API:** `/akm/v1`
- **Legacy (unversioned):** `/akm`
- **Health checks:** `/health`

---

## Next Steps

- 📖 [Authentication Guide](./AUTHENTICATION.md)
- 🚀 [Quick Start Guide](../README.md#quick-start)
- 🔧 [Admin Guide](./ADMIN_GUIDE.md)
- 📊 [API Reference](https://api.example.com/docs)
- 🐛 [Troubleshooting](./TROUBLESHOOTING.md)

---

## Support

- **GitHub Issues:** [github.com/ideiasfactory/akm/issues](https://github.com/ideiasfactory/akm/issues)
- **Documentation:** [github.com/ideiasfactory/akm/docs](https://github.com/ideiasfactory/akm/tree/main/docs)
- **Examples:** [github.com/ideiasfactory/akm/examples](https://github.com/ideiasfactory/akm/tree/main/examples)
