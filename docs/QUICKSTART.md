# 🚀 Quick Start Guide - Client Integration

Welcome! This guide will help you integrate your application with the API Key Management Service. You'll learn how to create credentials, define scopes, authenticate requests, and secure your routes.

## Table of Contents

- [Overview](#overview)
- [Step 1: Receive Your Credentials](#step-1-receive-your-credentials)
- [Step 2: Create Your Scopes](#step-2-create-your-scopes)
- [Step 3: Generate Additional API Keys](#step-3-generate-additional-api-keys)
- [Step 4: Import OpenAPI/Swagger Spec](#step-4-import-openapiswagger-spec)
- [Step 5: Authenticate Your Requests](#step-5-authenticate-your-requests)
- [Step 6: Instrument Your Routes](#step-6-instrument-your-routes)
- [Advanced Topics](#advanced-topics)
- [Code Examples](#code-examples)
- [Troubleshooting](#troubleshooting)

---

## Overview

The API Key Management Service provides a centralized way to manage API keys, scopes, and permissions for your applications.

### 🔐 Before You Start

⚠️ **Note**: The service administrator creates your project and generates your initial project admin API key. You'll receive these credentials via email. With this admin key, you can manage your own scopes, import your API specification, and generate additional keys.

Behind the scenes, the administrator:
1. Creates your project in the system
2. Generates your project admin API key
3. Sends you the credentials securely

Once you receive your credentials, you can:
- Create and manage your own scopes
- Import your OpenAPI/Swagger spec to auto-generate scopes
- Generate additional API keys for different environments
- Authenticate your API requests
- Instrument your application routes

👉 **Administrators**: See the [Administration Guide](/administration) for the complete onboarding process.

### What You'll Accomplish

Once you receive your credentials from the administrator, you'll:

1. ✅ **Receive your project admin API key** from the administrator
2. **Create and manage scopes** for your application
3. **Import your API spec** to auto-configure routes and scopes (optional)
4. **Generate additional keys** with specific permissions
5. **Authenticate requests** using your API keys
6. **Secure your routes** with middleware and decorators
7. **Monitor usage** and manage your keys

**Base URL**: `https://your-service.com/akm` (or `http://localhost:8002/akm` for local development)

**Your Admin Contact**: Contact your service administrator for initial setup and credentials.

---

## Step 1: Receive Your Credentials

⚠️ **This step is performed by the service administrator, not by you.**

The administrator will create your project and provide you with your project admin API key.

### What You'll Receive

You should receive an email or secure message containing:

```yaml
Project ID: proj_abc123xyz
Project Admin API Key: akm_live_s3cr3tk3yh3r3d0nts4v3m3
Rate Limit: 10,000 requests/hour
Expires: 2026-11-23 (or never)
```

### What the Admin Does

Behind the scenes, the administrator runs:

```bash
# Admin creates your project
curl -X POST "https://your-service.com/akm/v1/projects" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: akm_admin_..." \
  -d '{
    "name": "my-app-production",
    "description": "Production environment for My App"
  }'

# Admin generates your project admin API key
curl -X POST "https://your-service.com/akm/v1/keys" \
  -H "X-API-Key: akm_admin_..." \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_abc123xyz",
    "name": "project-admin-key",
    "rate_limit": 10000
  }'
```

With this project admin API key, you can now manage your own scopes and generate additional keys.

### Verify Your Access

Once you receive credentials, verify they work:

```bash
# Test authentication
curl -X GET "https://your-service.com/akm/v1/keys" \
  -H "X-API-Key: akm_live_s3cr3tk3yh3r3d0nts4v3m3"
```

**Success!** If you get a `200 OK` response with your key details, you're ready to proceed.

**Need credentials?** Contact your service administrator or email: `admin@your-service.com`

---

## Step 2: Create Your Scopes

With your project admin API key, you can now create scopes that define what actions your API keys can perform.

### Option A: Create Scopes Manually

```bash
curl -X POST "https://your-service.com/akm/v1/scopes" \
  -H "Content-Type: application/json\" \
  -H "X-API-Key: akm_live_s3cr3tk3yh3r3d0nts4v3m3" \
  -d '{
    "name": "users:read",
    "description": "View user information",
    "project_id": "proj_abc123xyz"
  }'
```

### Option B: Import from OpenAPI/Swagger Spec

Automatically generate scopes from your API specification:

```bash
curl -X POST "https://your-service.com/akm/v1/import/openapi" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: akm_live_s3cr3tk3yh3r3d0nts4v3m3" \
  -d '{
    "project_id": "proj_abc123xyz",
    "spec_url": "https://your-api.com/openapi.json",
    "auto_create_scopes": true,
    "scope_prefix": "api"
  }'
```

This will:
- Parse your OpenAPI spec
- Generate scopes for each endpoint (e.g., `GET /users` → `api:users:read`)
- Create them in your project
- Return a summary of created scopes

### List Your Created Scopes

```bash
curl -X GET "https://your-service.com/akm/v1/scopes?project_id=proj_abc123xyz" \
  -H "X-API-Key: akm_live_s3cr3tk3yh3r3d0nts4v3m3"
```

**Response Example:**

```json
{
  "scopes": [
    {
      "id": "scope_001",
      "name": "users:read",
      "description": "View user information"
    },
    {
      "id": "scope_002",
      "name": "users:write",
      "description": "Create and update users"
    }
  ]
}
```

---

## Step 3: Generate Additional API Keys

Now that you have scopes defined, you can create additional API keys with specific scopes for different environments or use cases.

### Development Key (Read-Only)

```bash
curl -X POST "https://your-service.com/akm/v1/keys" \
  -H "X-API-Key: akm_live_s3cr3tk3yh3r3d0nts4v3m3" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_abc123xyz",
    "name": "dev-readonly-key",
    "scopes": ["users:read", "orders:read"],
    "rate_limit": 100,
    "expires_at": "2026-12-31T23:59:59Z"
  }'
```

### Staging Key (Read + Write)

```bash
curl -X POST "https://your-service.com/akm/v1/keys" \
  -H "X-API-Key: akm_live_s3cr3tk3yh3r3d0nts4v3m3" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_abc123xyz",
    "name": "staging-api-key",
    "scopes": ["users:read", "users:write", "orders:read", "orders:write"],
    "rate_limit": 5000,
    "expires_at": "2026-06-30T23:59:59Z"
  }'
```

### Response

```json
{
  "id": "key_xyz789abc",
  "key": "akm_live_x9y8z7w6v5u4t3s2r1q0p9o8n7m6l5k4",
  "name": "staging-api-key",
  "scopes": ["users:read", "users:write", "orders:read", "orders:write"],
  "rate_limit": 5000,
  "created_at": "2025-11-23T10:15:00Z",
  "expires_at": "2026-06-30T23:59:59Z"
}
```

⚠️ **Important**: Save the `key` value immediately. It won't be shown again!

### List Your Keys

```bash
curl -X GET "https://your-service.com/akm/v1/keys?project_id=proj_abc123xyz" \
  -H "X-API-Key: akm_live_s3cr3tk3yh3r3d0nts4v3m3"
```

### Revoke a Key

```bash
curl -X DELETE "https://your-service.com/akm/v1/keys/key_xyz789abc" \
  -H "X-API-Key: akm_live_s3cr3tk3yh3r3d0nts4v3m3"
```

---

## Step 4: Import OpenAPI/Swagger Spec

Automatically configure routes and scopes by importing your OpenAPI/Swagger specification.

### Export Your Swagger Spec

If using FastAPI:

```python
# Your application
from fastapi import FastAPI
import json

app = FastAPI(title="My Application API")

# ... your routes ...

# Generate OpenAPI spec
if __name__ == "__main__":
    with open("openapi.json", "w") as f:
        json.dump(app.openapi(), f, indent=2)
```

Or visit: `http://your-app.com/openapi.json`

### Import to API Key Management

```bash
curl -X POST "https://your-service.com/akm/v1/import/openapi" \
  -H "X-API-Key: akm_live_s3cr3tk3yh3r3d0nts4v3m3" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_abc123xyz",
    "spec_url": "https://your-app.com/openapi.json"
  }'
```

Or upload file directly:

```bash
curl -X POST "https://your-service.com/akm/v1/import/openapi" \
  -H "X-API-Key: akm_live_s3cr3tk3yh3r3d0nts4v3m3" \
  -H "Content-Type: multipart/form-data" \
  -F "project_id=proj_abc123xyz" \
  -F "file=@openapi.json"
```

### What Gets Imported

The system automatically extracts:

- **Routes**: `/users`, `/users/{id}`, `/orders`, etc.
- **HTTP Methods**: `GET`, `POST`, `PUT`, `DELETE`
- **Scopes**: Generated from operation IDs or tags
- **Rate Limits**: From `x-rate-limit` extensions (if present)

### Response

```json
{
  "imported": {
    "routes": 25,
    "scopes": 8,
    "operations": 45
  },
  "scopes_created": [
    "users:read",
    "users:write",
    "orders:read",
    "orders:write",
    "products:read"
  ],
  "routes_mapped": [
    {"path": "/users", "methods": ["GET", "POST"], "scopes": ["users:read", "users:write"]},
    {"path": "/users/{id}", "methods": ["GET", "PUT", "DELETE"], "scopes": ["users:read", "users:write"]},
    {"path": "/orders", "methods": ["GET", "POST"], "scopes": ["orders:read", "orders:write"]}
  ]
}
```

---

## Step 5: Authenticate Your Requests

Use your API key in the `X-API-Key` header to authenticate requests.

### Basic Authentication

```bash
curl -X GET "https://your-app.com/api/users" \
  -H "X-API-Key: akm_live_s3cr3tk3yh3r3d0nts4v3m3"
```

### Python Example

```python
import httpx

API_KEY = "akm_live_s3cr3tk3yh3r3d0nts4v3m3"

async def get_users():
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://your-app.com/api/users",
            headers={"X-API-Key": API_KEY}
        )
        return response.json()

users = await get_users()
```

### JavaScript/TypeScript Example

```typescript
const API_KEY = "akm_live_s3cr3tk3yh3r3d0nts4v3m3";

async function getUsers() {
  const response = await fetch("https://your-app.com/api/users", {
    headers: {
      "X-API-Key": API_KEY,
    },
  });
  return response.json();
}

const users = await getUsers();
```

### Handling Authentication Errors

```python
import httpx

async def authenticated_request(url: str, api_key: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            url,
            headers={"X-API-Key": api_key}
        )
        
        if response.status_code == 401:
            raise Exception("Invalid API key")
        elif response.status_code == 403:
            raise Exception("Insufficient permissions (scope)")
        elif response.status_code == 429:
            raise Exception("Rate limit exceeded")
        
        response.raise_for_status()
        return response.json()
```

---

## Step 6: Instrument Your Routes

Add authentication and authorization to your application routes.

### FastAPI Integration

```python
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
import httpx

app = FastAPI()

# API Key header
api_key_header = APIKeyHeader(name="X-API-Key")

# Validation endpoint URL
VALIDATION_URL = "https://your-service.com/akm/v1/keys/validate"

async def validate_api_key(
    api_key: str = Security(api_key_header),
    required_scopes: list[str] = None
):
    """Validate API key and check scopes"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            VALIDATION_URL,
            json={
                "api_key": api_key,
                "required_scopes": required_scopes or []
            }
        )
        
        if response.status_code != 200:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired API key"
            )
        
        data = response.json()
        
        if not data.get("valid"):
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
        
        if not data.get("has_required_scopes"):
            raise HTTPException(
                status_code=403,
                detail=f"Missing required scopes: {data.get('missing_scopes')}"
            )
        
        return data

# Protected route - any authenticated user
@app.get("/api/users")
async def get_users(auth: dict = Depends(validate_api_key)):
    return {"users": [...], "authenticated_as": auth["project_id"]}

# Protected route - requires specific scope
@app.post("/api/users")
async def create_user(
    user_data: dict,
    auth: dict = Depends(lambda: validate_api_key(required_scopes=["users:write"]))
):
    # Only keys with "users:write" scope can access
    return {"message": "User created", "user": user_data}

# Admin-only route
@app.delete("/api/users/{user_id}")
async def delete_user(
    user_id: str,
    auth: dict = Depends(lambda: validate_api_key(required_scopes=["admin"]))
):
    # Only keys with "admin" scope can access
    return {"message": f"User {user_id} deleted"}
```

### Flask Integration

```python
from flask import Flask, request, jsonify
import httpx

app = Flask(__name__)

VALIDATION_URL = "https://your-service.com/akm/v1/keys/validate"

def validate_api_key(required_scopes=None):
    """Decorator for API key validation"""
    def decorator(f):
        def wrapped(*args, **kwargs):
            api_key = request.headers.get("X-API-Key")
            
            if not api_key:
                return jsonify({"error": "Missing API key"}), 401
            
            # Validate with sync client
            response = httpx.post(
                VALIDATION_URL,
                json={
                    "api_key": api_key,
                    "required_scopes": required_scopes or []
                }
            )
            
            if response.status_code != 200:
                return jsonify({"error": "Invalid API key"}), 401
            
            data = response.json()
            
            if not data.get("valid"):
                return jsonify({"error": "Invalid API key"}), 401
            
            if not data.get("has_required_scopes"):
                return jsonify({
                    "error": "Insufficient permissions",
                    "missing_scopes": data.get("missing_scopes")
                }), 403
            
            # Pass auth data to route
            request.auth_data = data
            return f(*args, **kwargs)
        
        wrapped.__name__ = f.__name__
        return wrapped
    return decorator

@app.route("/api/users", methods=["GET"])
@validate_api_key()
def get_users():
    return jsonify({"users": [...], "project": request.auth_data["project_id"]})

@app.route("/api/users", methods=["POST"])
@validate_api_key(required_scopes=["users:write"])
def create_user():
    return jsonify({"message": "User created"})
```

### Express.js Integration

```javascript
const express = require("express");
const axios = require("axios");

const app = express();
const VALIDATION_URL = "https://your-service.com/akm/v1/keys/validate";

// Middleware for API key validation
const validateApiKey = (requiredScopes = []) => {
  return async (req, res, next) => {
    const apiKey = req.headers["x-api-key"];

    if (!apiKey) {
      return res.status(401).json({ error: "Missing API key" });
    }

    try {
      const response = await axios.post(VALIDATION_URL, {
        api_key: apiKey,
        required_scopes: requiredScopes,
      });

      const data = response.data;

      if (!data.valid) {
        return res.status(401).json({ error: "Invalid API key" });
      }

      if (!data.has_required_scopes) {
        return res.status(403).json({
          error: "Insufficient permissions",
          missing_scopes: data.missing_scopes,
        });
      }

      // Attach auth data to request
      req.authData = data;
      next();
    } catch (error) {
      return res.status(401).json({ error: "Authentication failed" });
    }
  };
};

// Protected routes
app.get("/api/users", validateApiKey(), (req, res) => {
  res.json({ users: [...], project: req.authData.project_id });
});

app.post("/api/users", validateApiKey(["users:write"]), (req, res) => {
  res.json({ message: "User created" });
});

app.delete("/api/users/:id", validateApiKey(["admin"]), (req, res) => {
  res.json({ message: `User ${req.params.id} deleted` });
});

app.listen(3000);
```

---

## Advanced Topics

### Rate Limiting

Check remaining rate limit in responses:

```python
async def make_request_with_rate_limit_check(url: str, api_key: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers={"X-API-Key": api_key})
        
        # Check rate limit headers
        remaining = response.headers.get("X-RateLimit-Remaining")
        limit = response.headers.get("X-RateLimit-Limit")
        reset = response.headers.get("X-RateLimit-Reset")
        
        print(f"Rate limit: {remaining}/{limit}, resets at {reset}")
        
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            raise Exception(f"Rate limited. Retry after {retry_after} seconds")
        
        return response.json()
```

### Key Rotation

Rotate keys without downtime:

```python
async def rotate_api_key(old_key: str):
    """Generate new key and revoke old one"""
    
    # 1. Generate new key with same scopes
    new_key = await generate_key(
        project_id=project_id,
        name="rotated-key",
        scopes=["users:read", "users:write"]
    )
    
    # 2. Update your application with new key
    update_application_config(api_key=new_key["key"])
    
    # 3. Test new key
    await test_api_key(new_key["key"])
    
    # 4. Revoke old key
    await revoke_key(old_key)
    
    return new_key
```

### Webhooks for Key Events

Subscribe to key events:

```bash
curl -X POST "https://your-service.com/akm/v1/webhooks" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "proj_abc123xyz",
    "url": "https://your-app.com/webhooks/key-events",
    "events": ["key.created", "key.revoked", "key.expired"],
    "secret": "webhook_secret_for_validation"
  }'
```

Handle webhook events:

```python
from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib

@app.post("/webhooks/key-events")
async def handle_key_event(request: Request):
    # Verify webhook signature
    signature = request.headers.get("X-Webhook-Signature")
    body = await request.body()
    
    expected = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if signature != expected:
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Process event
    event = await request.json()
    
    if event["type"] == "key.expired":
        # Notify admin
        await notify_admin(f"Key {event['key_id']} expired")
    
    return {"status": "received"}
```

### Audit Logs

Query audit trail for compliance:

```bash
curl -X GET "https://your-service.com/akm/v1/audit-logs?project_id=proj_abc123xyz&limit=100"
```

---

## Code Examples

### Complete Python Client

```python
import httpx
from typing import Optional

class APIKeyManagementClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient()
    
    async def create_project(self, name: str, description: str = ""):
        response = await self.client.post(
            f"{self.base_url}/v1/projects",
            json={"name": name, "description": description}
        )
        response.raise_for_status()
        return response.json()
    
    async def create_scope(self, name: str, project_id: str, description: str = ""):
        response = await self.client.post(
            f"{self.base_url}/v1/scopes",
            json={"name": name, "project_id": project_id, "description": description}
        )
        response.raise_for_status()
        return response.json()
    
    async def generate_key(
        self,
        project_id: str,
        name: str,
        scopes: list[str],
        rate_limit: Optional[int] = None,
        expires_at: Optional[str] = None
    ):
        response = await self.client.post(
            f"{self.base_url}/v1/keys",
            json={
                "project_id": project_id,
                "name": name,
                "scopes": scopes,
                "rate_limit": rate_limit,
                "expires_at": expires_at
            }
        )
        response.raise_for_status()
        return response.json()
    
    async def validate_key(self, api_key: str, required_scopes: list[str] = None):
        response = await self.client.post(
            f"{self.base_url}/v1/keys/validate",
            json={"api_key": api_key, "required_scopes": required_scopes or []}
        )
        response.raise_for_status()
        return response.json()

# Usage
client = APIKeyManagementClient("https://your-service.com/akm")

# Setup
project = await client.create_project("my-app", "My Application")
await client.create_scope("users:read", project["id"])
await client.create_scope("users:write", project["id"])

# Generate key
key = await client.generate_key(
    project_id=project["id"],
    name="prod-key",
    scopes=["users:read", "users:write"],
    rate_limit=10000
)

print(f"Your API Key: {key['key']}")
```

---

## Troubleshooting

### 401 Unauthorized

**Issue**: `{"error": "Invalid or expired API key"}`

**Solutions**:
- Verify key is correct (no extra spaces)
- Check key hasn't expired
- Ensure key hasn't been revoked
- Verify header name is `X-API-Key` (case-sensitive)

### 403 Forbidden

**Issue**: `{"error": "Insufficient permissions", "missing_scopes": ["users:write"]}`

**Solutions**:
- Check key has required scopes
- Generate new key with additional scopes
- Update existing key permissions

### 429 Rate Limited

**Issue**: `{"error": "Rate limit exceeded"}`

**Solutions**:
- Wait for rate limit reset (check `Retry-After` header)
- Upgrade to higher rate limit tier
- Implement exponential backoff
- Cache responses when possible

### Import Errors

**Issue**: OpenAPI import fails

**Solutions**:
- Verify OpenAPI spec is valid JSON/YAML
- Check spec version (3.0.x or 3.1.x supported)
- Ensure URL is accessible
- Validate spec at https://editor.swagger.io/

---

## Next Steps

✅ **You're ready to integrate!** Here's what to do next:

1. **Create your first project and API key**
2. **Import your OpenAPI spec** for auto-configuration
3. **Add authentication middleware** to your routes
4. **Test with different scopes** to verify permissions
5. **Set up rate limiting** for production
6. **Configure webhooks** for key lifecycle events
7. **Review audit logs** for compliance

### Additional Resources

- [Administration Guide](/administration) - **For administrators**: Setup, user onboarding, monitoring
- [API Versioning Guide](/api-versioning) - Using `/v1`, `/v2` endpoints
- [Authentication Patterns](/authentication) - Advanced auth strategies
- [Rate Limiting](/api-key-management) - Configure rate limits
- [Webhooks](/api-key-management#webhooks) - Event notifications
- [Full API Reference](/docs) - Interactive documentation

---

**Questions?** Open an issue on [GitHub](https://github.com/ideiasfactory/apikey_management/issues) or check the [discussions](https://github.com/ideiasfactory/apikey_management/discussions).

Happy integrating! 🚀
