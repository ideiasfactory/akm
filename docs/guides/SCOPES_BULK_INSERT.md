# Scopes Bulk Insert Guide

Complete guide for bulk importing scopes into AKM.

## Table of Contents

- [Overview](#overview)
- [Bulk Insert via JSON](#bulk-insert-via-json)
- [Bulk Insert via File Upload](#bulk-insert-via-file-upload)
- [Generate from OpenAPI Spec](#generate-from-openapi-spec)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)

---

## Overview

Bulk operations allow you to create or update multiple scopes in a single request. This is ideal for:

- Initial project setup
- Migrating from other systems
- Synchronizing with OpenAPI specifications
- Managing large scope sets

### Supported Methods

1. **JSON Payload** - Send scopes directly in request body
2. **File Upload** - Upload JSON file with scopes
3. **OpenAPI Generation** - Auto-generate from Swagger/OpenAPI spec

---

## Bulk Insert via JSON

### Endpoint

```
POST /akm/v1/projects/{project_id}/scopes/bulk
```

### Request Format

```json
{
  "scopes": [
    {
      "scope_name": "akm:users:read",
      "description": "Read user data",
      "resource_type": "users",
      "action": "read",
      "metadata": {
        "category": "user_management",
        "endpoints": ["/users", "/users/{id}"]
      }
    },
    {
      "scope_name": "akm:users:write",
      "description": "Create and update users",
      "resource_type": "users",
      "action": "write",
      "metadata": {
        "category": "user_management",
        "endpoints": ["/users"]
      }
    }
  ]
}
```

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `scope_name` | string | Unique scope identifier (format: `prefix:resource:action`) |
| `description` | string | Human-readable description |
| `resource_type` | string | Resource being protected (e.g., "users", "projects") |
| `action` | string | Action allowed (e.g., "read", "write", "delete") |

### Optional Fields

| Field | Type | Description |
|-------|------|-------------|
| `metadata` | object | Custom key-value data |
| `is_active` | boolean | Enable/disable scope (default: true) |
| `parent_scope` | string | Parent scope for hierarchical permissions |

### Example Request

```bash
curl -X POST "https://api.example.com/akm/v1/projects/1/scopes/bulk" \
  -H "X-API-Key: akm_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "scopes": [
      {
        "scope_name": "akm:products:read",
        "description": "Read product catalog",
        "resource_type": "products",
        "action": "read"
      },
      {
        "scope_name": "akm:products:write",
        "description": "Manage product catalog",
        "resource_type": "products",
        "action": "write"
      },
      {
        "scope_name": "akm:orders:read",
        "description": "View orders",
        "resource_type": "orders",
        "action": "read"
      }
    ]
  }'
```

### Response Format

```json
{
  "total_processed": 3,
  "created": 2,
  "updated": 1,
  "skipped": 0,
  "errors": [],
  "scope_names": [
    "akm:products:read",
    "akm:products:write",
    "akm:orders:read"
  ]
}
```

### Response Fields

| Field | Type | Description |
|-------|------|-------------|
| `total_processed` | int | Total scopes in request |
| `created` | int | New scopes created |
| `updated` | int | Existing scopes updated |
| `skipped` | int | Scopes skipped (duplicates, no changes) |
| `errors` | array | List of errors encountered |
| `scope_names` | array | Names of all processed scopes |

---

## Bulk Insert via File Upload

### Endpoint

```
POST /akm/v1/projects/{project_id}/scopes/bulk/file
```

### File Format

Upload a JSON file with the same structure as the JSON payload:

**scopes.json:**
```json
{
  "scopes": [
    {
      "scope_name": "akm:api:read",
      "description": "Read API endpoints",
      "resource_type": "api",
      "action": "read"
    },
    {
      "scope_name": "akm:api:write",
      "description": "Modify API configuration",
      "resource_type": "api",
      "action": "write"
    }
  ]
}
```

### Example Request

```bash
curl -X POST "https://api.example.com/akm/v1/projects/1/scopes/bulk/file" \
  -H "X-API-Key: akm_your_key_here" \
  -F "file=@scopes.json"
```

### Python Example

```python
import requests

url = "https://api.example.com/akm/v1/projects/1/scopes/bulk/file"
headers = {"X-API-Key": "akm_your_key_here"}

with open("scopes.json", "rb") as f:
    files = {"file": ("scopes.json", f, "application/json")}
    response = requests.post(url, headers=headers, files=files)

print(response.json())
```

---

## Generate from OpenAPI Spec

Automatically generate scopes from your OpenAPI/Swagger specification.

### Endpoint

```
POST /akm/v1/openapi-scopes/generate/{project_id}
```

### Request Format

```json
{
  "openapi_url": "https://api.example.com/openapi.json",
  "prefix": "akm",
  "auto_apply": false,
  "mapping_rules": {
    "GET": "read",
    "POST": "write",
    "PUT": "write",
    "PATCH": "write",
    "DELETE": "delete"
  }
}
```

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `openapi_url` | string | Yes | URL to OpenAPI/Swagger spec (JSON or YAML) |
| `prefix` | string | No | Scope prefix (default: "akm") |
| `auto_apply` | boolean | No | Auto-create scopes (default: false) |
| `mapping_rules` | object | No | HTTP method to action mapping |

### How It Works

1. **Fetch OpenAPI spec** from provided URL
2. **Parse endpoints** and extract:
   - Paths (e.g., `/users/{id}`)
   - HTTP methods (GET, POST, etc.)
   - Tags (group related endpoints)
   - Operation IDs
3. **Generate scopes** using pattern:
   ```
   {prefix}:{resource}:{action}
   ```
4. **Return preview** or auto-create if `auto_apply: true`

### Example: OpenAPI Spec

```yaml
openapi: 3.0.0
paths:
  /users:
    get:
      tags: [Users]
      operationId: listUsers
      summary: List all users
    post:
      tags: [Users]
      operationId: createUser
      summary: Create new user
  /users/{id}:
    get:
      tags: [Users]
      operationId: getUser
      summary: Get user by ID
    delete:
      tags: [Users]
      operationId: deleteUser
      summary: Delete user
```

### Generated Scopes

```json
{
  "project_id": 1,
  "total_generated": 3,
  "scopes": [
    {
      "scope_name": "akm:users:read",
      "description": "Read user data (from OpenAPI)",
      "resource_type": "users",
      "action": "read",
      "metadata": {
        "source": "openapi",
        "endpoints": ["/users", "/users/{id}"],
        "methods": ["GET"],
        "operations": ["listUsers", "getUser"]
      }
    },
    {
      "scope_name": "akm:users:write",
      "description": "Create and update users (from OpenAPI)",
      "resource_type": "users",
      "action": "write",
      "metadata": {
        "source": "openapi",
        "endpoints": ["/users"],
        "methods": ["POST"],
        "operations": ["createUser"]
      }
    },
    {
      "scope_name": "akm:users:delete",
      "description": "Delete users (from OpenAPI)",
      "resource_type": "users",
      "action": "delete",
      "metadata": {
        "source": "openapi",
        "endpoints": ["/users/{id}"],
        "methods": ["DELETE"],
        "operations": ["deleteUser"]
      }
    }
  ],
  "applied": false
}
```

### Auto-Apply Example

```bash
curl -X POST "https://api.example.com/akm/v1/openapi-scopes/generate/1" \
  -H "X-API-Key: akm_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "openapi_url": "https://api.example.com/openapi.json",
    "prefix": "akm",
    "auto_apply": true
  }'
```

Response includes `"applied": true` and scopes are immediately created.

---

## Best Practices

### Naming Conventions

✅ **Good:**
```
akm:users:read
akm:products:write
akm:orders:delete
akm:admin:*
```

❌ **Bad:**
```
read_users
WRITE-PRODUCTS
orders_delete_permission
```

**Rules:**
- Use lowercase
- Colon-separated format: `prefix:resource:action`
- Consistent resource names (plural recommended)
- Standard actions: read, write, delete, admin, *

### Resource Organization

Group related scopes by resource:

```json
{
  "scopes": [
    // User management
    {"scope_name": "akm:users:read", ...},
    {"scope_name": "akm:users:write", ...},
    {"scope_name": "akm:users:delete", ...},
    
    // Product catalog
    {"scope_name": "akm:products:read", ...},
    {"scope_name": "akm:products:write", ...},
    
    // Order processing
    {"scope_name": "akm:orders:read", ...},
    {"scope_name": "akm:orders:write", ...}
  ]
}
```

### Metadata Best Practices

Include helpful metadata:

```json
{
  "scope_name": "akm:payments:write",
  "description": "Process payments and refunds",
  "resource_type": "payments",
  "action": "write",
  "metadata": {
    "category": "financial",
    "risk_level": "high",
    "requires_mfa": true,
    "endpoints": [
      "/payments/charge",
      "/payments/refund"
    ],
    "documentation": "https://docs.example.com/payments"
  }
}
```

### Idempotency

Bulk insert is **idempotent**:
- Existing scopes are updated (based on `scope_name`)
- New scopes are created
- No duplicates are created

Safe to run multiple times with the same data.

### Error Handling

```json
{
  "total_processed": 5,
  "created": 3,
  "updated": 1,
  "skipped": 0,
  "errors": [
    {
      "scope_name": "invalid:scope",
      "error": "Invalid scope name format"
    }
  ],
  "scope_names": [
    "akm:users:read",
    "akm:users:write",
    "akm:products:read"
  ]
}
```

Individual errors don't stop the entire batch. Successfully processed scopes are still created/updated.

---

## Troubleshooting

### Common Errors

#### 1. Invalid Scope Name Format

```json
{
  "error": "Invalid scope name format",
  "detail": "Scope name must match pattern: prefix:resource:action"
}
```

**Solution:** Use colon-separated format: `akm:resource:action`

#### 2. Duplicate Scope Names in Request

```json
{
  "error": "Duplicate scope names in request",
  "duplicates": ["akm:users:read"]
}
```

**Solution:** Remove duplicate entries from your JSON.

#### 3. Project Not Found

```json
{
  "error": "Project not found",
  "project_id": 999
}
```

**Solution:** Verify project ID exists and you have access.

#### 4. Insufficient Permissions

```json
{
  "error": "Insufficient permissions",
  "required_scope": "akm:scopes:write"
}
```

**Solution:** Ensure your API key has `akm:scopes:write` or `akm:*` scope.

#### 5. File Too Large

```json
{
  "error": "File too large",
  "max_size": "10MB",
  "received": "15MB"
}
```

**Solution:** Split large files into smaller batches (recommended: 100-500 scopes per request).

### Validation

Before bulk import, validate your JSON:

```bash
# Using Python
python -m json.tool scopes.json

# Using jq
jq . scopes.json
```

### Testing

Test with a small batch first:

```bash
# Test with 2-3 scopes
curl -X POST "https://api.example.com/akm/v1/projects/1/scopes/bulk" \
  -H "X-API-Key: akm_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "scopes": [
      {
        "scope_name": "akm:test:read",
        "description": "Test scope",
        "resource_type": "test",
        "action": "read"
      }
    ]
  }'
```

---

## Examples

### Complete E-commerce Scopes

```json
{
  "scopes": [
    {
      "scope_name": "akm:products:read",
      "description": "View product catalog",
      "resource_type": "products",
      "action": "read"
    },
    {
      "scope_name": "akm:products:write",
      "description": "Manage products",
      "resource_type": "products",
      "action": "write"
    },
    {
      "scope_name": "akm:inventory:read",
      "description": "Check inventory levels",
      "resource_type": "inventory",
      "action": "read"
    },
    {
      "scope_name": "akm:inventory:write",
      "description": "Update inventory",
      "resource_type": "inventory",
      "action": "write"
    },
    {
      "scope_name": "akm:orders:read",
      "description": "View orders",
      "resource_type": "orders",
      "action": "read"
    },
    {
      "scope_name": "akm:orders:write",
      "description": "Process orders",
      "resource_type": "orders",
      "action": "write"
    },
    {
      "scope_name": "akm:customers:read",
      "description": "View customer data",
      "resource_type": "customers",
      "action": "read"
    },
    {
      "scope_name": "akm:payments:write",
      "description": "Process payments",
      "resource_type": "payments",
      "action": "write"
    },
    {
      "scope_name": "akm:shipping:write",
      "description": "Manage shipping",
      "resource_type": "shipping",
      "action": "write"
    },
    {
      "scope_name": "akm:admin:*",
      "description": "Full admin access",
      "resource_type": "admin",
      "action": "*"
    }
  ]
}
```

### Hierarchical Permissions

```json
{
  "scopes": [
    {
      "scope_name": "akm:resources:*",
      "description": "All resource operations",
      "resource_type": "resources",
      "action": "*"
    },
    {
      "scope_name": "akm:resources:read",
      "description": "Read resources",
      "resource_type": "resources",
      "action": "read",
      "parent_scope": "akm:resources:*"
    },
    {
      "scope_name": "akm:resources:write",
      "description": "Write resources",
      "resource_type": "resources",
      "action": "write",
      "parent_scope": "akm:resources:*"
    }
  ]
}
```

---

## Next Steps

- 📖 [Developer Guide](./DEVELOPER_GUIDE.md)
- 🔑 [Authentication Guide](./AUTHENTICATION.md)
- 🚀 [Quick Start](../README.md#quick-start)

---

## Support

Having issues with bulk import? [Open an issue](https://github.com/ideiasfactory/akm/issues) with:
- Sample JSON (redact sensitive data)
- Error response
- Project ID and scope count
