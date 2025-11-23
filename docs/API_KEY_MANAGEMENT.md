# API Key Management Guide

## Overview

This comprehensive guide covers how to manage API keys in the API Key Management (AKM) Service. Learn about creating, securing, rotating, and monitoring API keys for your projects.

## Table of Contents

- [Key Concepts](#key-concepts)
- [Key Lifecycle](#key-lifecycle)
- [Creating API Keys](#creating-api-keys)
- [Managing Scopes](#managing-scopes)
- [Security Best Practices](#security-best-practices)
- [Key Rotation](#key-rotation)
- [Monitoring and Usage](#monitoring-and-usage)
- [Incident Response](#incident-response)
- [FAQ](#faq)

---

## Key Concepts

### What is an API Key?

An API key is a unique identifier used to authenticate requests to the AKM service. Each key:

- **Belongs to a project**: Keys are scoped to specific projects
- **Has permissions**: Controlled by assigned scopes
- **Is hashed**: Only SHA-256 hashes are stored
- **Can expire**: Optional expiration dates
- **Has rate limits**: Requests per hour limits
- **Tracks usage**: Monitors request count and last usage

### Key Types

AKM supports two key environments:

1. **Live Keys** (``akm_live_*``): For production use
2. **Test Keys** (``akm_test_*``): For development and testing

---

## Key Lifecycle

```
┌─────────────┐
│   CREATE    │ → Generate new key with scopes and metadata
└──────┬──────┘
       ↓
┌─────────────┐
│   ACTIVE    │ → Key is usable for API requests
└──────┬──────┘
       ↓
┌─────────────┐
│  REVOKED    │ → Key is disabled (reversible)
└──────┬──────┘
       ↓
┌─────────────┐
│  DELETED    │ → Key is permanently removed (irreversible)
└─────────────┘
```

---

## Creating API Keys

### Step 1: Identify Requirements

Before creating a key, determine:

- **Project**: Which project needs access?
- **Scopes**: What permissions are required?
- **Environment**: Production (live) or development (test)?
- **Rate Limit**: How many requests per hour?
- **Expiration**: Should the key expire automatically?

### Step 2: Create the Key

**API Request:**

```bash
curl -X POST "https://api-service.com/akm/v1/keys" \
  -H "X-API-Key: akm_live_your_admin_key" \
  -H "Content-Type: application/json" \
  -d ''{
    "project_id": "proj_123",
    "name": "Production Frontend",
    "scopes": ["users:read", "orders:read"],
    "rate_limit_per_hour": 10000,
    "environment": "production",
    "expires_at": "2026-12-31T23:59:59Z"
  }''
```

**Response:**

```json
{
  "id": "key_789",
  "key": "akm_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
  "project_id": "proj_123",
  "name": "Production Frontend",
  "scopes": ["users:read", "orders:read"],
  "rate_limit_per_hour": 10000,
  "environment": "production",
  "created_at": "2025-11-23T10:00:00Z",
  "expires_at": "2026-12-31T23:59:59Z"
}
```

⚠️ **IMPORTANT**: Save the ``key`` value immediately. It will never be shown again.

---

## Managing Scopes

### Understanding Scopes

Scopes define what actions an API key can perform. They follow the format:

```
<resource>:<action>
```

**Common Scopes:**

- ``users:read`` - Read user data
- ``users:write`` - Create/update users
- ``users:delete`` - Delete users
- ``orders:read`` - Read order data
- ``orders:write`` - Create/update orders
- ``admin:full`` - Full administrative access

### Adding Scopes to a Key

```bash
curl -X POST "https://api-service.com/akm/v1/keys/key_789/scopes" \
  -H "X-API-Key: akm_live_your_admin_key" \
  -H "Content-Type: application/json" \
  -d ''{
    "scopes": ["products:read"]
  }''
```

### Removing Scopes

```bash
curl -X DELETE "https://api-service.com/akm/v1/keys/key_789/scopes" \
  -H "X-API-Key: akm_live_your_admin_key" \
  -H "Content-Type: application/json" \
  -d ''{
    "scopes": ["users:delete"]
  }''
```

---

## Security Best Practices

### 1. Key Storage

**✅ DO:**

- Store keys in environment variables
- Use secret management systems (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault)
- Use ``.env`` files for local development (never commit them)
- Encrypt keys at rest in your applications

**❌ DON''T:**

- Hard-code keys in source code
- Commit keys to version control
- Share keys via email or chat
- Store keys in plain text files
- Log keys in application logs

### 2. Key Naming

Use descriptive names to identify key purpose:

**Good Examples:**
```
"Production Frontend - User Dashboard"
"Development - API Testing"
"CI/CD Pipeline - GitHub Actions"
"Partner Integration - CompanyX"
```

**Bad Examples:**
```
"key1"
"test"
"my_key"
```

### 3. Principle of Least Privilege

Only grant the minimum required scopes:

```json
{
  "name": "Read-Only Dashboard",
  "scopes": ["users:read", "orders:read"]
}
```

### 4. Environment Separation

Create separate keys for each environment:

- **Development**: ``akm_test_*`` keys with relaxed limits
- **Staging**: ``akm_test_*`` or ``akm_live_*`` keys mimicking production
- **Production**: ``akm_live_*`` keys with strict controls

---

## Key Rotation

### Why Rotate Keys?

Regular key rotation enhances security by:

- Limiting exposure time if a key is compromised
- Following compliance requirements
- Maintaining security hygiene

### Rotation Schedule

- **Production keys**: Every 90 days
- **Development keys**: Every 180 days
- **Immediately**: If compromised or suspected breach

### Rotation Process

**Step 1: Create new key**

```bash
curl -X POST "https://api-service.com/akm/v1/keys" \
  -H "X-API-Key: akm_live_your_admin_key" \
  -H "Content-Type: application/json" \
  -d ''{
    "project_id": "proj_123",
    "name": "Production Frontend (Rotated)",
    "scopes": ["users:read", "orders:read"],
    "rate_limit_per_hour": 10000
  }''
```

**Step 2: Update applications**

Deploy the new key to your applications using your secret management system.

**Step 3: Grace period**

Keep both keys active for 24-48 hours to ensure smooth transition.

**Step 4: Revoke old key**

```bash
curl -X POST "https://api-service.com/akm/v1/keys/key_789/revoke" \
  -H "X-API-Key: akm_live_your_admin_key"
```

**Step 5: Monitor**

Check logs for any 401 errors indicating applications still using the old key.

---

## Monitoring and Usage

### View Key Details

```bash
curl -X GET "https://api-service.com/akm/v1/keys/key_789" \
  -H "X-API-Key: akm_live_your_admin_key"
```

**Response:**

```json
{
  "id": "key_789",
  "name": "Production Frontend",
  "project_id": "proj_123",
  "scopes": ["users:read", "orders:read"],
  "rate_limit_per_hour": 10000,
  "request_count": 45678,
  "last_used_at": "2025-11-23T09:45:00Z",
  "created_at": "2025-11-23T10:00:00Z",
  "expires_at": "2026-12-31T23:59:59Z",
  "is_revoked": false
}
```

### List All Keys

```bash
curl -X GET "https://api-service.com/akm/v1/projects/proj_123/keys" \
  -H "X-API-Key: akm_live_your_admin_key"
```

### Usage Metrics

Monitor these key metrics:

- **request_count**: Total requests made
- **last_used_at**: Last successful authentication
- **Rate limit consumption**: Check ``X-RateLimit-Remaining`` headers
- **Error rates**: Track 401/403 responses

---

## Incident Response

### If a Key is Compromised

**Immediate Actions (within 5 minutes):**

1. **Revoke the key:**
   ```bash
   curl -X POST "https://api-service.com/akm/v1/keys/key_789/revoke" \
     -H "X-API-Key: akm_live_your_admin_key"
   ```

2. **Create replacement key:**
   ```bash
   curl -X POST "https://api-service.com/akm/v1/keys" \
     -H "X-API-Key: akm_live_your_admin_key" \
     -H "Content-Type: application/json" \
     -d ''{"project_id": "proj_123", "name": "Emergency Replacement", ...}''
   ```

3. **Update all services** using the compromised key

**Follow-up Actions (within 24 hours):**

4. **Audit access logs** to check for unauthorized usage
5. **Review how the compromise occurred**
6. **Document the incident** and lessons learned
7. **Update security procedures** if needed

### If You Lose a Key

Keys cannot be recovered. You must:

1. Create a new key with the same permissions
2. Update your application configuration
3. Revoke the old key (or let it expire)

---

## FAQ

### Q: Can I recover a lost API key?

**A:** No. Keys are hashed using SHA-256, which is irreversible. If you lose a key, create a new one.

### Q: How many keys can I create?

**A:** There''s no hard limit, but we recommend:
- 1-2 keys per application
- Separate keys for each environment
- Separate keys for each integration partner

### Q: Can I temporarily disable a key?

**A:** Yes, use the revoke endpoint. You can later re-enable it by updating the ``is_revoked`` field.

### Q: What happens when rate limit is exceeded?

**A:** The API returns ``429 Too Many Requests`` with headers indicating when the limit resets.

### Q: How do I increase my rate limit?

**A:** Update the key:
```bash
curl -X PATCH "https://api-service.com/akm/v1/keys/key_789" \
  -H "X-API-Key: akm_live_your_admin_key" \
  -H "Content-Type: application/json" \
  -d ''{"rate_limit_per_hour": 50000}''
```

### Q: Can I use the same key for multiple applications?

**A:** While possible, we recommend creating separate keys for:
- Better monitoring and debugging
- Easier key rotation
- Granular access control
- Independent rate limiting

### Q: What''s the difference between revoked and deleted keys?

**A:**
- **Revoked**: Disabled but preserved in database for audit trails
- **Deleted**: Permanently removed from database

### Q: How do I test if my key is working?

**A:** Make a test request:
```bash
curl -X GET "https://api-service.com/akm/v1/health" \
  -H "X-API-Key: akm_live_your_key"
```

---

## Additional Resources

- [Quick Start Guide](/quickstart) - Getting started with AKM
- [Administration Guide](/administration) - Managing the AKM service
- [Authentication Guide](/authentication) - Authentication patterns
- [API Versioning](/api-versioning) - API version management

---

**Need Help?** Check the [GitHub Issues](https://github.com/ideiasfactory/apikey_management/issues).
