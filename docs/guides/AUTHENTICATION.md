# Authentication Guide - API Key Management Service

## Overview

The API Key Management (AKM) Service provides a comprehensive authentication and authorization system based on API keys with scope-based permissions. This guide covers authentication patterns, security features, and best practices for integrating with the AKM service.

## Table of Contents

- [Authentication Methods](#authentication-methods)
- [API Key Structure](#api-key-structure)
- [Scope-Based Authorization](#scope-based-authorization)
- [Authentication Patterns](#authentication-patterns)
- [Security Features](#security-features)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Code Examples](#code-examples)

---

## Authentication Methods

AKM supports **API Key Authentication** via the `X-API-Key` header. This method is simple, secure, and suitable for both server-to-server and client-to-server communication.

### API Key Format

```
akm_live_<32-character-base64-string>
akm_test_<32-character-base64-string>
```

**Examples:**
- Production: ``akm_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6``
- Test: ``akm_test_x9y8z7w6v5u4t3s2r1q0p9o8n7m6l5k4``

### Making Authenticated Requests

Include your API key in the `X-API-Key` header:

```bash
curl -X GET "https://api-service.com/akm/v1/projects" \
  -H "X-API-Key: akm_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
```

---

## API Key Structure

Each API key in AKM has:

1. **Project Association**: Keys belong to a specific project
2. **Scopes**: Define what actions the key can perform
3. **Rate Limit**: Maximum requests per hour
4. **Expiration**: Optional expiration date
5. **Metadata**: Name, description, environment tags

---

## Scope-Based Authorization

Scopes control what actions an API key can perform. AKM enforces scope-based authorization on all endpoints.

### Scope Naming Convention

```
<resource>:<action>
```

**Examples:**
- ``users:read`` - Read user data
- ``users:write`` - Create/update users
- ``orders:read`` - Read order data
- ``orders:write`` - Create/update orders
- ``admin:full`` - Full administrative access

---

## Authentication Patterns

### Pattern 1: Direct API Key Usage

Best for: Server-to-server communication, background jobs

```python
import requests

API_KEY = "akm_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
BASE_URL = "https://api-service.com/akm/v1"

headers = {"X-API-Key": API_KEY}

# List projects
response = requests.get(f"{BASE_URL}/projects", headers=headers)
projects = response.json()
```

### Pattern 2: FastAPI Middleware

```python
from fastapi import FastAPI, Header, HTTPException, Depends
import requests

app = FastAPI()

async def verify_api_key(x_api_key: str = Header(...)):
    """Verify API key with AKM service"""
    response = requests.get(
        f"https://api-service.com/akm/v1/keys/verify",
        headers={"X-API-Key": x_api_key}
    )
    
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return response.json()

@app.get("/users")
async def get_users(key_info: dict = Depends(verify_api_key)):
    return {"users": [...]}
```

---

## Security Features

### 1. SHA-256 Key Hashing

API keys are hashed using SHA-256 before storage. Only the hash is stored in the database.

### 2. Automatic Expiration

Keys can have expiration dates. Expired keys are automatically rejected.

### 3. Usage Tracking

Every request increments the ``request_count`` and updates ``last_used_at``.

### 4. Audit Logging

All authentication attempts are logged with timestamp, API key ID, success/failure status, IP address, and user agent.

---

## Rate Limiting

Each API key has a rate limit (requests per hour). When exceeded, requests return ``429 Too Many Requests``.

### Rate Limit Headers

Every response includes:

```http
X-RateLimit-Limit: 10000
X-RateLimit-Remaining: 9523
X-RateLimit-Reset: 1700000000
```

---

## Error Handling

### Common Authentication Errors

#### 401 Unauthorized - Missing API Key

```json
{
  "status": "client_error",
  "error_message": "Missing API key"
}
```

**Solution**: Include ``X-API-Key`` header.

#### 401 Unauthorized - Invalid API Key

```json
{
  "status": "client_error",
  "error_message": "Invalid or expired API key"
}
```

**Possible causes:**
- Key is incorrect
- Key has been revoked
- Key has expired

#### 403 Forbidden - Insufficient Permissions

```json
{
  "status": "client_error",
  "error_message": "Insufficient permissions"
}
```

**Solution**: Use an API key with the required scopes.

#### 429 Too Many Requests

```json
{
  "status": "client_error",
  "error_message": "Rate limit exceeded"
}
```

**Solution**: Wait for rate limit reset or request higher limit.

---

## Best Practices

### 1. Store Keys Securely

✅ **DO:**
```python
import os
API_KEY = os.getenv("AKM_API_KEY")
```

❌ **DON''T:**
```python
API_KEY = "akm_live_a1b2c3d4..."  # Hardcoded!
```

### 2. Use Environment Variables

```bash
# .env file (never commit this!)
AKM_API_KEY=akm_live_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
```

### 3. Rotate Keys Regularly

Create new keys every 90 days and revoke old ones.

### 4. Use Minimal Scopes

Request only the scopes you need.

### 5. Monitor Usage

Check key usage statistics regularly.

### 6. Handle Errors Gracefully

Implement retry logic and proper error handling.

---

## Code Examples

### Python Client

```python
import os
import requests

class AKMClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api-service.com/akm/v1"
        self.headers = {"X-API-Key": api_key}
    
    def list_projects(self):
        response = requests.get(f"{self.base_url}/projects", headers=self.headers)
        response.raise_for_status()
        return response.json()

# Usage
client = AKMClient(os.getenv("AKM_API_KEY"))
projects = client.list_projects()
```

### TypeScript Client

```typescript
import axios from ''axios'';

class AKMClient {
  private apiKey: string;
  private baseURL: string;
  
  constructor(apiKey: string) {
    this.apiKey = apiKey;
    this.baseURL = ''https://api-service.com/akm/v1'';
  }
  
  async listProjects() {
    const response = await axios.get(`${this.baseURL}/projects`, {
      headers: { ''X-API-Key'': this.apiKey }
    });
    return response.data;
  }
}
```

---

## Additional Resources

- [Quick Start Guide](/quickstart) - Getting started with AKM
- [Administration Guide](/public/guides/admnistration.html) - Managing the AKM service
- [API Versioning](/api-versioning) - API version management
- [API Reference](/docs) - Complete API documentation

---

**Need Help?** Check the [GitHub Issues](https://github.com/ideiasfactory/akm/issues).
