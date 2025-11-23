"""seed_initial_data

Revision ID: 36af276ef713
Revises: e1dd99f6c0b2
Create Date: 2025-11-20 23:30:48.092178

Seeds initial data:
- Default AKM project with prefix 'akm'
- All default scopes (projects, keys, scopes, webhooks, alerts, sensitive-fields, usage, admin)
- Webhook event types
- Admin API key with full access
- GLOBAL sensitive fields (project_id=NULL) that apply to all projects by default
"""
from typing import Sequence, Union
from datetime import datetime
import hashlib
import secrets
from pathlib import Path

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '36af276ef713'
down_revision: Union[str, None] = 'e1dd99f6c0b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Default webhook events
WEBHOOK_EVENTS = [
    ("rate_limit_reached", "Triggered when an API key reaches its rate limit (per minute/hour)"),
    ("daily_limit_reached", "Triggered when an API key reaches its daily request limit"),
    ("monthly_limit_reached", "Triggered when an API key reaches its monthly request limit"),
    ("daily_limit_warning", "Triggered when daily usage reaches 80% of limit"),
    ("monthly_limit_warning", "Triggered when monthly usage reaches 80% of limit"),
    ("api_key_created", "Triggered when a new API key is created"),
    ("api_key_revoked", "Triggered when an API key is revoked"),
    ("api_key_deleted", "Triggered when an API key is permanently deleted"),
    ("api_key_config_changed", "Triggered when API key configuration is updated"),
    ("suspicious_activity", "Triggered on potential security issues (invalid IP, time restrictions)"),
    ("project_created", "Triggered when a new project is created"),
    ("project_deleted", "Triggered when a project is deleted"),
    ("alert_triggered", "Triggered when an alert rule condition is met"),
    ("webhook_delivery_failed", "Triggered when webhook delivery fails after all retries"),
    ("scope_violation", "Triggered when an API key attempts to access resources without proper scopes"),
]

# Default scopes for AKM project (project_id will be 1)
DEFAULT_SCOPES = [
    # Project scopes
    ("akm:projects:read", "View projects"),
    ("akm:projects:write", "Create and update projects"),
    ("akm:projects:delete", "Delete projects"),
    ("akm:projects:*", "Full project access"),
    
    # API Key scopes
    ("akm:keys:read", "View API keys"),
    ("akm:keys:write", "Create and update API keys"),
    ("akm:keys:delete", "Delete API keys"),
    ("akm:keys:*", "Full API key access"),
    
    # Scope management
    ("akm:scopes:read", "View scopes"),
    ("akm:scopes:write", "Create and update scopes"),
    ("akm:scopes:delete", "Delete scopes"),
    ("akm:scopes:*", "Full scope access"),
    
    # Webhook scopes
    ("akm:webhooks:read", "View webhooks"),
    ("akm:webhooks:write", "Create and update webhooks"),
    ("akm:webhooks:delete", "Delete webhooks"),
    ("akm:webhooks:*", "Full webhook access"),
    
    # Alert scopes
    ("akm:alerts:read", "View alerts"),
    ("akm:alerts:write", "Create and update alerts"),
    ("akm:alerts:delete", "Delete alerts"),
    ("akm:alerts:*", "Full alert access"),
    
    # Usage stats
    ("akm:usage:read", "View usage statistics"),
    
    # Sensitive Fields scopes
    ("akm:sensitive-fields:read", "View sensitive field rules"),
    ("akm:sensitive-fields:create", "Create sensitive field rules"),
    ("akm:sensitive-fields:update", "Update sensitive field rules"),
    ("akm:sensitive-fields:delete", "Delete sensitive field rules"),
    ("akm:sensitive-fields:*", "Full sensitive fields access"),
    
    # Admin scopes
    ("akm:admin:read", "Admin read access"),
    ("akm:admin:write", "Admin write access"),
    ("akm:admin:*", "Full admin access"),
    
    # Wildcard
    ("akm:*", "Full system access (super admin)"),
]

# GLOBAL sensitive fields (project_id=NULL) - apply to ALL projects by default
# Projects can override these or add their own project-specific fields
GLOBAL_SENSITIVE_FIELDS = [
    "password",
    "token",
    "secret",
    "api_key",
    "key_hash",
    "authorization",
    "x-api-key",
    "bearer",
    "credential",
    "private_key",
    "client_secret",
]


def generate_api_key() -> str:
    """Generate a secure API key"""
    return f"akm_{secrets.token_urlsafe(32)}"


def hash_key(plain_key: str) -> str:
    """Hash API key with SHA-256"""
    return hashlib.sha256(plain_key.encode()).hexdigest()


def upgrade() -> None:
    conn = op.get_bind()
    
    # 1. Create AKM Admin Project
    print("Creating AKM Admin project...")
    result = conn.execute(text("""
        INSERT INTO akm_projects (name, prefix, description, is_active, created_at)
        VALUES ('AKM Admin', 'akm', 'API Key Management administrative project', true, NOW())
        RETURNING id
    """))
    project_id = result.fetchone()[0]
    print(f"✅ Project created with ID: {project_id}")
    
    # 2. Insert webhook events
    print(f"\nInserting {len(WEBHOOK_EVENTS)} webhook events...")
    for event_type, description in WEBHOOK_EVENTS:
        conn.execute(text("""
            INSERT INTO akm_webhook_events (event_type, description, is_active, created_at)
            VALUES (:event_type, :description, true, NOW())
        """), {"event_type": event_type, "description": description})
    print(f"✅ {len(WEBHOOK_EVENTS)} webhook events inserted")
    
    # 3. Insert scopes and collect their IDs
    print(f"\nInserting {len(DEFAULT_SCOPES)} scopes for project {project_id}...")
    admin_scope_id = None
    for scope_name, description in DEFAULT_SCOPES:
        result = conn.execute(text("""
            INSERT INTO akm_scopes (project_id, scope_name, description, is_active, created_at)
            VALUES (:project_id, :scope_name, :description, true, NOW())
            RETURNING id
        """), {"project_id": project_id, "scope_name": scope_name, "description": description})
        
        # Save the ID of the akm:* scope for later use
        if scope_name == "akm:*":
            admin_scope_id = result.fetchone()[0]
    
    print(f"✅ {len(DEFAULT_SCOPES)} scopes inserted")
    print(f"   Admin scope (akm:*) ID: {admin_scope_id}")
    
    # 4. Insert GLOBAL sensitive fields (project_id=NULL)
    print(f"\n🌍 Inserting {len(GLOBAL_SENSITIVE_FIELDS)} GLOBAL sensitive fields (apply to all projects)...")
    for field_name in GLOBAL_SENSITIVE_FIELDS:
        conn.execute(text("""
            INSERT INTO akm_sensitive_fields 
            (project_id, field_name, is_active, strategy, replacement, created_at, updated_at)
            VALUES (NULL, :field_name, true, 'redact', '[REDACTED]', NOW(), NOW())
        """), {"field_name": field_name.lower()})
    print(f"✅ {len(GLOBAL_SENSITIVE_FIELDS)} global sensitive fields inserted")
    print(f"   These fields apply to ALL projects by default")
    print(f"   Projects can override or add project-specific fields")
    
    # 5. Create admin API key
    print("\nCreating admin API key...")
    plain_key = generate_api_key()
    key_hash = hash_key(plain_key)
    
    result = conn.execute(text("""
        INSERT INTO akm_api_keys 
        (project_id, key_hash, name, description, is_active, created_at, request_count)
        VALUES (:project_id, :key_hash, 'Admin Master Key', 
                'Full system access for administrative tasks', true, NOW(), 0)
        RETURNING id
    """), {"project_id": project_id, "key_hash": key_hash})
    api_key_id = result.fetchone()[0]
    
    # 6. Assign akm:* scope to admin key (using scope_id now)
    conn.execute(text("""
        INSERT INTO akm_api_key_scopes (api_key_id, scope_id, created_at)
        VALUES (:api_key_id, :scope_id, NOW())
    """), {"api_key_id": api_key_id, "scope_id": admin_scope_id})
    
    # 7. Create default config for admin key
    conn.execute(text("""
        INSERT INTO akm_api_key_configs (api_key_id, rate_limit_enabled, ip_whitelist_enabled)
        VALUES (:api_key_id, false, false)
    """), {"api_key_id": api_key_id})
    
    print(f"✅ Admin API key created with ID: {api_key_id}")
    print("\n" + "=" * 80)
    print("⚠️  IMPORTANT: Save this API key - it will not be shown again!")
    print("=" * 80)
    print(f"\nAPI Key: {plain_key}")
    print("\nAdd to .env file:")
    print(f"ADMIN_API_KEY={plain_key}")
    print("=" * 80 + "\n")
    
    # Save to file for reference
    try:
        key_file = Path(__file__).parent.parent.parent / "ADMIN_API_KEY.txt"
        with open(key_file, 'w') as f:
            f.write(f"Admin API Key (Generated: {datetime.now().isoformat()})\n")
            f.write("=" * 80 + "\n")
            f.write(f"{plain_key}\n")
            f.write("=" * 80 + "\n")
            f.write(f"\nProject ID: {project_id}\n")
            f.write(f"Project Prefix: akm\n")
            f.write(f"API Key ID: {api_key_id}\n")
            f.write(f"Scope ID: {admin_scope_id} (akm:*)\n")
            f.write(f"\nScopes: akm:* (full system access)\n")
            f.write(f"Total Scopes: {len(DEFAULT_SCOPES)}\n")
            f.write(f"Total Global Sensitive Fields: {len(GLOBAL_SENSITIVE_FIELDS)}\n")
            f.write(f"Total Webhook Events: {len(WEBHOOK_EVENTS)}\n")
            f.write("\n" + "=" * 80 + "\n")
            f.write("GLOBAL SENSITIVE FIELDS (apply to ALL projects):\n")
            f.write("=" * 80 + "\n")
            for field in GLOBAL_SENSITIVE_FIELDS:
                f.write(f"  - {field}\n")
            f.write("\nProjects can override these or add their own project-specific fields.\n")
        print(f"💾 API key also saved to: {key_file}")
    except Exception as e:
        print(f"⚠️  Could not save key to file: {e}")


def downgrade() -> None:
    conn = op.get_bind()
    
    print("Rolling back seed data...")
    
    # Delete in reverse order to respect foreign keys
    conn.execute(text("DELETE FROM akm_api_key_configs"))
    conn.execute(text("DELETE FROM akm_api_key_scopes"))
    conn.execute(text("DELETE FROM akm_api_keys"))
    conn.execute(text("DELETE FROM akm_sensitive_fields"))  # Deletes both global and project-specific
    conn.execute(text("DELETE FROM akm_scopes"))
    conn.execute(text("DELETE FROM akm_webhook_events"))
    conn.execute(text("DELETE FROM akm_projects"))
    
    print("✅ All seed data removed")
