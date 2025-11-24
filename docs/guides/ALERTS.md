# Alerts Guide

Automated monitoring and notifications for API key events.

## Overview

Set up alerts to receive notifications when important events occur:

- 🚦 Rate limits approaching/exceeded
- 🛡️ Security violations (unauthorized IP, scope violations)
- ⏰ Key expiration warnings
- 📊 Unusual usage patterns
- 🔧 System events

## Alert Types

| Type | Trigger Condition | Example |
|------|-------------------|---------|
| `RATE_LIMIT_THRESHOLD` | Usage > threshold % | 80% of hourly limit reached |
| `RATE_LIMIT_EXCEEDED` | Limit exceeded | 1000/1000 requests used |
| `IP_VIOLATION` | Request from unauthorized IP | 203.0.113.42 not in allowlist |
| `SCOPE_VIOLATION` | Insufficient permissions | Needs `akm:users:write` |
| `EXPIRY_WARNING` | Key expiring soon | Expires in 7 days |
| `USAGE_ANOMALY` | Unusual pattern | 10x normal traffic |
| `SUSPICIOUS_ACTIVITY` | Multiple violations | 5 failed auth attempts |

---

## Creating Alerts

### Endpoint

```bash
POST /akm/v1/projects/{project_id}/keys/{key_id}/alerts
```

### Rate Limit Alert

```bash
POST /akm/v1/projects/1/keys/42/alerts
Content-Type: application/json

{
  "alert_type": "RATE_LIMIT_THRESHOLD",
  "threshold": 80,
  "enabled": true,
  "notification_channels": ["webhook", "email"],
  "webhook_url": "https://your-app.com/alerts",
  "email_recipients": ["ops@example.com", "team@example.com"],
  "cooldown_minutes": 30,
  "metadata": {
    "severity": "warning",
    "team": "platform"
  }
}
```

### IP Violation Alert

```bash
POST /akm/v1/projects/1/keys/42/alerts
{
  "alert_type": "IP_VIOLATION",
  "enabled": true,
  "notification_channels": ["webhook"],
  "webhook_url": "https://security.example.com/alerts",
  "cooldown_minutes": 5,
  "metadata": {
    "severity": "critical",
    "auto_block": true
  }
}
```

### Expiry Warning

```bash
POST /akm/v1/projects/1/keys/42/alerts
{
  "alert_type": "EXPIRY_WARNING",
  "threshold": 7,
  "enabled": true,
  "notification_channels": ["email"],
  "email_recipients": ["admin@example.com"]
}
```

---

## Alert Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `alert_type` | string | Yes | Type of alert (see types above) |
| `threshold` | integer | Conditional | Percentage/days threshold |
| `enabled` | boolean | No | Enable/disable (default: true) |
| `notification_channels` | array | Yes | ["webhook", "email"] |
| `webhook_url` | string | If webhook | URL to POST alert to |
| `email_recipients` | array | If email | Email addresses |
| `cooldown_minutes` | integer | No | Min time between alerts (default: 30) |
| `metadata` | object | No | Custom key-value data |

---

## Alert Payload

Alerts are delivered via webhook or email with this structure:

```json
{
  "alert_id": 123,
  "alert_type": "RATE_LIMIT_THRESHOLD",
  "api_key_id": 42,
  "project_id": 1,
  "triggered_at": "2025-11-23T21:30:00Z",
  "severity": "warning",
  "details": {
    "current_usage": 850,
    "limit": 1000,
    "percentage": 85.0,
    "window": "per_hour",
    "reset_at": "2025-11-23T22:00:00Z"
  },
  "recommended_actions": [
    "Consider increasing rate limit",
    "Monitor usage patterns",
    "Contact support if needed"
  ],
  "correlation_id": "alert_abc123"
}
```

---

## Managing Alerts

### List Alerts

```bash
GET /akm/v1/projects/{project_id}/keys/{key_id}/alerts
```

### Get Alert Details

```bash
GET /akm/v1/projects/{project_id}/keys/{key_id}/alerts/{alert_id}
```

### Update Alert

```bash
PUT /akm/v1/projects/{project_id}/keys/{key_id}/alerts/{alert_id}
{
  "threshold": 90,
  "enabled": true
}
```

### Delete Alert

```bash
DELETE /akm/v1/projects/{project_id}/keys/{key_id}/alerts/{alert_id}
```

---

## Alert History

View past alerts:

```bash
GET /akm/v1/alerts/history?key_id=42&days=7
```

Response:
```json
{
  "total": 15,
  "alerts": [
    {
      "alert_id": 123,
      "alert_type": "RATE_LIMIT_THRESHOLD",
      "triggered_at": "2025-11-23T21:30:00Z",
      "resolved_at": "2025-11-23T21:45:00Z",
      "duration_minutes": 15,
      "details": {
        "percentage": 85.0
      }
    }
  ]
}
```

---

## Alert Statistics

Aggregate metrics:

```bash
GET /akm/v1/alerts/stats?project_id=1&period=7d
```

Response:
```json
{
  "period": "7d",
  "total_alerts": 42,
  "by_type": {
    "RATE_LIMIT_THRESHOLD": 20,
    "IP_VIOLATION": 10,
    "SCOPE_VIOLATION": 8,
    "EXPIRY_WARNING": 4
  },
  "by_severity": {
    "critical": 5,
    "warning": 25,
    "info": 12
  },
  "most_triggered": [
    {
      "key_id": 42,
      "count": 15,
      "alert_type": "RATE_LIMIT_THRESHOLD"
    }
  ]
}
```

---

## Cooldown Period

Prevents alert spam by enforcing minimum time between notifications:

```bash
{
  "cooldown_minutes": 30
}
```

**Example:**
- Alert triggers at 21:00
- Next alert can trigger at 21:30 or later
- Violations during cooldown are logged but not notified

---

## Notification Channels

### Webhook

POST request to your endpoint with alert payload:

```http
POST https://your-app.com/alerts
Content-Type: application/json
X-Alert-Signature: <hmac-signature>

{
  "alert_id": 123,
  "alert_type": "RATE_LIMIT_THRESHOLD",
  ...
}
```

### Email

HTML formatted email with:
- Alert summary
- Key details
- Recommended actions
- Link to dashboard

---

## Common Alert Configurations

### 1. Rate Limit Monitoring

```bash
# Warning at 80%
POST /akm/v1/projects/1/keys/42/alerts
{
  "alert_type": "RATE_LIMIT_THRESHOLD",
  "threshold": 80,
  "notification_channels": ["email"],
  "email_recipients": ["ops@example.com"],
  "cooldown_minutes": 60
}

# Critical at 95%
POST /akm/v1/projects/1/keys/42/alerts
{
  "alert_type": "RATE_LIMIT_THRESHOLD",
  "threshold": 95,
  "notification_channels": ["webhook", "email"],
  "webhook_url": "https://pagerduty.com/webhook",
  "email_recipients": ["oncall@example.com"],
  "cooldown_minutes": 15
}
```

### 2. Security Monitoring

```bash
POST /akm/v1/projects/1/keys/42/alerts
{
  "alert_type": "IP_VIOLATION",
  "notification_channels": ["webhook"],
  "webhook_url": "https://security.example.com/incidents",
  "cooldown_minutes": 5,
  "metadata": {
    "severity": "critical",
    "auto_revoke": false
  }
}
```

### 3. Key Lifecycle

```bash
POST /akm/v1/projects/1/keys/42/alerts
{
  "alert_type": "EXPIRY_WARNING",
  "threshold": 30,
  "notification_channels": ["email"],
  "email_recipients": ["admin@example.com"]
}
```

---

## Best Practices

### 1. Appropriate Thresholds

- **80%** - Warning, review needed
- **90%** - Action required  
- **95%** - Critical, immediate attention

### 2. Cooldown Configuration

- **High frequency events** (rate limits): 30-60 min
- **Security events**: 5-15 min
- **Lifecycle events**: No cooldown

### 3. Notification Routing

```bash
# Development keys - email only
{
  "notification_channels": ["email"],
  "email_recipients": ["dev-team@example.com"]
}

# Production keys - webhook + email
{
  "notification_channels": ["webhook", "email"],
  "webhook_url": "https://pagerduty.com/webhook",
  "email_recipients": ["oncall@example.com"]
}
```

### 4. Metadata for Context

```json
{
  "metadata": {
    "environment": "production",
    "service": "api-gateway",
    "team": "platform",
    "severity": "high",
    "runbook": "https://wiki.example.com/runbooks/rate-limits"
  }
}
```

---

## Handling Alerts

### Webhook Handler Example

```python
from fastapi import FastAPI, Request
import hmac
import hashlib

app = FastAPI()

@app.post("/alerts")
async def handle_alert(request: Request):
    payload = await request.json()
    
    alert_type = payload["alert_type"]
    
    if alert_type == "RATE_LIMIT_THRESHOLD":
        # Check if approaching limit
        percentage = payload["details"]["percentage"]
        
        if percentage >= 95:
            # Critical - page on-call
            await page_oncall(payload)
        elif percentage >= 80:
            # Warning - notify team
            await notify_team(payload)
    
    elif alert_type == "IP_VIOLATION":
        # Security event - auto-block if configured
        if payload.get("metadata", {}).get("auto_block"):
            await block_ip(payload["details"]["ip_address"])
        
        # Always log security events
        await log_security_incident(payload)
    
    return {"status": "processed"}
```

---

## Troubleshooting

### Alert Not Triggering

1. Check alert is enabled
2. Verify threshold configuration
3. Check cooldown period hasn't elapsed
4. Review alert history for recent triggers

### Too Many Alerts

1. Increase cooldown period
2. Adjust threshold (make less sensitive)
3. Review and disable noisy alerts
4. Use aggregation/batching

### Webhook Delivery Fails

1. Verify endpoint is accessible
2. Check webhook URL is correct
3. Ensure endpoint returns 2xx status
4. Review alert delivery logs

---

## Next Steps

- 📖 [Developer Guide](./DEVELOPER_GUIDE.md)
- 🔔 [Webhooks](./WEBHOOKS.md)
- 🚦 [Configuration Guide](./CONFIGURATION_GUIDE.md)

---

**Support:** [Open an issue](https://github.com/ideiasfactory/akm/issues) for alert-related questions.
