# Sensitive Field Management System

## Overview

The Sensitive Field Management System provides dynamic, configurable sanitization of sensitive data in audit logs and other outputs. It supports multiple sanitization strategies (redact, mask) with field-level configuration control.

## Features

- **Dynamic Configuration**: Define sensitive fields via JSON file, database, or environment variables
- **Multiple Strategies**: Choose between redaction (full replacement) or masking (partial visibility)
- **Merge Priority**: DB overrides file config, field-level settings override global defaults
- **CRUD API**: Manage sensitive field configurations via REST API
- **Automatic Caching**: 5-minute TTL cache for optimal performance
- **Flexible Masking**: Configure leading/trailing characters to show and masking character

## Architecture

### Components

1. **Database Model**: `AKMSensitiveField` - Stores field configurations
2. **Repository**: `SensitiveFieldRepository` - CRUD operations
3. **Manager**: `SensitiveFieldManager` - Merges config from multiple sources
4. **API Routes**: `/akm/sensitive-fields/*` - REST endpoints
5. **Integration**: `AuditLogger` uses manager for sanitization

### Configuration Sources (Priority Order)

1. **File**: `data/sensitive_fields.json` (lowest priority)
2. **Database**: `akm_sensitive_fields` table (medium priority)
3. **Environment**: Global settings in `.env` (default fallback)
4. **Per-Field Override**: Field-specific settings (highest priority)

## Configuration

### Environment Variables (.env)

```env
# Global sanitization defaults
SANITIZATION_STRATEGY=redact           # redact | mask
SANITIZATION_REPLACEMENT=[REDACTED]    # For redact strategy
SANITIZATION_MASK_SHOW_START=3         # Leading chars to show when masking
SANITIZATION_MASK_SHOW_END=2           # Trailing chars to show when masking
SANITIZATION_MASK_CHAR=*               # Masking character
```

### File Configuration (data/sensitive_fields.json)

```json
{
  "fields": [
    "password",
    "token",
    "secret",
    "api_key",
    "authorization"
  ],
  "strategy": "redact",
  "replacement": "[REDACTED]",
  "mask": {
    "show_start": 3,
    "show_end": 2,
    "char": "*"
  }
}
```

### Database Model

```python
class AKMSensitiveField(Base):
    id: int
    field_name: str                    # Case-insensitive
    is_active: bool                    # Enable/disable field
    strategy: Optional[str]            # "redact" | "mask" (overrides global)
    mask_show_start: Optional[int]     # Leading chars (overrides global)
    mask_show_end: Optional[int]       # Trailing chars (overrides global)
    mask_char: Optional[str]           # Masking char (overrides global)
    replacement: Optional[str]         # Replacement text (overrides global)
    created_at: datetime
    updated_at: datetime
```

## API Endpoints

### List Sensitive Fields

```bash
GET /akm/sensitive-fields?active=true
```

**Required Scope**: `akm:sensitive-fields:read`

**Response**:
```json
{
  "total": 5,
  "items": [
    {
      "id": 1,
      "field_name": "password",
      "is_active": true,
      "strategy": "redact",
      "mask_show_start": null,
      "mask_show_end": null,
      "mask_char": null,
      "replacement": "[HIDDEN]"
    }
  ]
}
```

### Get Single Field

```bash
GET /akm/sensitive-fields/{field_id}
```

**Required Scope**: `akm:sensitive-fields:read`

### Create Sensitive Field

```bash
POST /akm/sensitive-fields
Content-Type: application/json

{
  "field_name": "credit_card",
  "is_active": true,
  "strategy": "mask",
  "mask_show_start": 4,
  "mask_show_end": 4,
  "mask_char": "*"
}
```

**Required Scope**: `akm:sensitive-fields:create`

**Response**:
```json
{
  "id": 10,
  "field_name": "credit_card",
  "is_active": true,
  "strategy": "mask",
  "mask_show_start": 4,
  "mask_show_end": 4,
  "mask_char": "*",
  "replacement": null
}
```

### Update Sensitive Field

```bash
PUT /akm/sensitive-fields/{field_id}
Content-Type: application/json

{
  "strategy": "redact",
  "replacement": "[CARD_REDACTED]"
}
```

**Required Scope**: `akm:sensitive-fields:update`

### Delete Sensitive Field

```bash
DELETE /akm/sensitive-fields/{field_id}
```

**Required Scope**: `akm:sensitive-fields:delete`

## Sanitization Strategies

### 1. Redact (Full Replacement)

Replaces entire value with a fixed string.

**Configuration**:
```json
{
  "field_name": "password",
  "strategy": "redact",
  "replacement": "[REDACTED]"
}
```

**Example**:
```
Input:  {"password": "MySecretPass123"}
Output: {"password": "[REDACTED]"}
```

### 2. Mask (Partial Visibility)

Shows leading and trailing characters, masks the middle.

**Configuration**:
```json
{
  "field_name": "api_key",
  "strategy": "mask",
  "mask_show_start": 6,
  "mask_show_end": 4,
  "mask_char": "*"
}
```

**Example**:
```
Input:  {"api_key": "sk_live_abc123xyz789def456"}
Output: {"api_key": "sk_liv*************f456"}
```

**Edge Cases**:
- If value length ≤ (show_start + show_end): entire value masked
- Example: `"abc"` with show_start=3, show_end=2 → `"***"`

## Usage Examples

### 1. Add New Sensitive Field via API

```bash
curl -X POST http://localhost:8000/akm/sensitive-fields \
  -H "X-API-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "ssn",
    "is_active": true,
    "strategy": "mask",
    "mask_show_start": 0,
    "mask_show_end": 4,
    "mask_char": "X"
  }'
```

### 2. Update Strategy for Existing Field

```bash
curl -X PUT http://localhost:8000/akm/sensitive-fields/5 \
  -H "X-API-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "strategy": "redact",
    "replacement": "[SSN_HIDDEN]"
  }'
```

### 3. Programmatic Usage in Python

```python
from src.sensitive_field_manager import SensitiveFieldManager

# Initialize manager
manager = SensitiveFieldManager(db_session)

# Load configuration (file + DB merge)
await manager.load()

# Check if field is sensitive
is_sensitive = await manager.is_sensitive("password")  # True

# Get field-specific config
config = await manager.get_field_config("api_key")
# Returns: {"strategy": "mask", "mask_show_start": 3, ...}

# Get global defaults
global_config = manager.get_global_strategy()
```

### 4. Integration with AuditLogger

The `AuditLogger` automatically uses `SensitiveFieldManager`:

```python
from src.audit_logger import AuditLogger

logger = AuditLogger(db_session)

# Sensitive data is automatically sanitized based on configuration
await logger.log_operation(
    operation="update_user",
    resource_type="user",
    action="PUT",
    request_payload={
        "username": "john",
        "password": "secret123",      # Will be sanitized
        "api_key": "sk_live_abc123"   # Will be sanitized
    }
)
```

## Scopes

The sensitive field management system requires specific scopes:

| Scope | Description |
|-------|-------------|
| `akm:sensitive-fields:read` | List and view sensitive field configurations |
| `akm:sensitive-fields:create` | Create new sensitive field configuration |
| `akm:sensitive-fields:update` | Update existing sensitive field configuration |
| `akm:sensitive-fields:delete` | Delete sensitive field configuration |
| `akm:sensitive-fields:*` | Full CRUD access (wildcard) |

### Creating Management Key

```bash
# Create API key with full sensitive fields access
curl -X POST http://localhost:8000/akm/keys \
  -H "X-API-Key: $ADMIN_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 1,
    "name": "Sensitive Fields Manager",
    "scope_names": ["akm:sensitive-fields:*"]
  }'
```

## Merge Logic

Configuration sources are merged with the following priority:

1. **File** (`data/sensitive_fields.json`): Base configuration
2. **Database** (`akm_sensitive_fields`): Overrides file settings
3. **Global Defaults** (environment): Used when field-specific config is NULL

**Example Merge**:

**File**:
```json
{
  "fields": ["password", "token"],
  "strategy": "redact"
}
```

**Database**:
```sql
INSERT INTO akm_sensitive_fields (field_name, strategy, mask_show_start, mask_show_end)
VALUES ('password', 'mask', 2, 2);  -- Overrides file strategy
```

**Result**:
- `password`: Uses **mask** strategy (DB override) with show_start=2, show_end=2
- `token`: Uses **redact** strategy (file default)
- Any new field: Uses global env defaults

## Performance

- **Caching**: Configuration cached for 5 minutes (300 seconds)
- **Cache TTL**: Configurable via `CACHE_TTL_SECONDS` constant
- **Force Reload**: Call `manager.load(force=True)` to bypass cache
- **Lazy Loading**: Configuration loaded on first use only

## Migration

Database migration creates the `akm_sensitive_fields` table:

```bash
# Run migration
alembic upgrade head

# Verify table created
psql -d your_database -c "\d akm_sensitive_fields"
```

## Best Practices

### 1. Default Strategy Selection

- **Redact**: For highly sensitive data (passwords, secrets, private keys)
- **Mask**: For identifiable data that needs partial visibility (API keys, emails, phone numbers)

### 2. Masking Configuration

- **API Keys**: Show prefix/suffix for identification
  - Example: `show_start=6, show_end=4` → `"sk_liv*************f456"`
- **Credit Cards**: Show last 4 digits only
  - Example: `show_start=0, show_end=4` → `"************1234"`
- **Emails**: Show first char and domain
  - Example: Custom logic needed (not just masking)

### 3. Field Naming

- Use lowercase field names (system normalizes to lowercase)
- Use exact match or substring match (e.g., "password" matches "user_password", "password_hash")

### 4. Database vs File

- **File**: Bootstrap/default configuration for all environments
- **Database**: Runtime overrides, project-specific customization
- **Environment**: Global defaults when no other config exists

### 5. Security

- Restrict `akm:sensitive-fields:*` scope to admin users only
- Audit all changes to sensitive field configurations
- Review sanitization logs periodically to ensure effectiveness

## Troubleshooting

### Field Not Being Sanitized

1. Check if field is in configuration:
   ```bash
   curl http://localhost:8000/akm/sensitive-fields -H "X-API-Key: $KEY"
   ```

2. Verify field is active:
   ```bash
   GET /akm/sensitive-fields?active=true
   ```

3. Check cache (may need 5 minutes to refresh):
   ```python
   await manager.load(force=True)  # Force reload
   ```

### Incorrect Masking Output

1. Verify masking configuration:
   - Check `mask_show_start`, `mask_show_end`, `mask_char`
   - Ensure values are reasonable for typical data length

2. Test with sample data:
   ```python
   # Value: "1234567890"
   # show_start=2, show_end=2, mask_char="*"
   # Result: "12******90"
   ```

### Database Override Not Working

1. Ensure database entry exists and is active
2. Clear cache: Wait 5 minutes or restart service
3. Check merge order in logs

## Future Enhancements

- [ ] Custom sanitization functions (regex-based, format-preserving)
- [ ] Per-project sensitive field configuration
- [ ] Field pattern matching (regex support)
- [ ] Audit trail for configuration changes
- [ ] Bulk import/export of configurations
- [ ] Real-time cache invalidation
- [ ] Sensitive data detection (AI/ML-based)

## Related Documentation

- [Audit System](./AUDIT_SYSTEM.md) - Audit logging with automatic sanitization
- [API Authentication](./AUTHENTICATION.md) - API key and scope management
- [Configuration](./ENVIRONMENT.md) - Environment variable reference
