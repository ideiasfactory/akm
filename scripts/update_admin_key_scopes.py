"""
Add project configuration scopes to admin API key.

This script adds the new project configuration scopes to the existing
admin API key (ID: 6) if they're not already assigned.

Usage:
    python scripts/update_admin_key_scopes.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.connection import get_engine
from src.database.models import AKMAPIKey, AKMAPIKeyScope, AKMScope
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.logging_config import get_logger

logger = get_logger(__name__)

ADMIN_KEY_ID = 6
AKM_PROJECT_ID = 1

# Scopes to add (if not already assigned)
NEW_SCOPE_NAMES = [
    "akm:projects:config:read",
    "akm:projects:config:write",
    "akm:projects:config:delete",
    "akm:projects:config:*"
]


def update_admin_key_scopes():
    """
    Add project configuration scopes to admin key.
    """
    engine = get_engine()
    
    with Session(engine) as session:
        try:
            # Get admin key
            admin_key = session.execute(
                select(AKMAPIKey).where(AKMAPIKey.id == ADMIN_KEY_ID)
            ).scalar_one_or_none()
            
            if not admin_key:
                print(f"❌ ERROR: Admin API key with ID {ADMIN_KEY_ID} not found!")
                return False
            
            print(f"✅ Found Admin Key: {admin_key.name} (ID: {admin_key.id})")
            print()
            
            # Check if admin already has akm:* scope
            existing_scopes = session.execute(
                select(AKMAPIKeyScope)
                .where(AKMAPIKeyScope.api_key_id == ADMIN_KEY_ID)
            ).scalars().all()
            
            for key_scope in existing_scopes:
                scope = session.execute(
                    select(AKMScope).where(AKMScope.id == key_scope.scope_id)
                ).scalar_one()
                
                if scope.scope_name == "akm:*":
                    print("✅ Admin key already has 'akm:*' scope (full access)")
                    print("   No need to add individual scopes.")
                    print()
                    return True
            
            # Add new scopes
            added_count = 0
            skipped_count = 0
            
            for scope_name in NEW_SCOPE_NAMES:
                # Get scope
                scope = session.execute(
                    select(AKMScope).where(
                        AKMScope.project_id == AKM_PROJECT_ID,
                        AKMScope.scope_name == scope_name
                    )
                ).scalar_one_or_none()
                
                if not scope:
                    print(f"⚠️  WARNING: Scope '{scope_name}' not found in database!")
                    print("   Run seed_project_config_scopes.py first.")
                    continue
                
                # Check if already assigned
                existing = session.execute(
                    select(AKMAPIKeyScope).where(
                        AKMAPIKeyScope.api_key_id == ADMIN_KEY_ID,
                        AKMAPIKeyScope.scope_id == scope.id
                    )
                ).scalar_one_or_none()
                
                if existing:
                    print(f"⏭️  SKIPPED: {scope_name} (already assigned)")
                    skipped_count += 1
                    continue
                
                # Add scope to key
                key_scope = AKMAPIKeyScope(
                    api_key_id=ADMIN_KEY_ID,
                    scope_id=scope.id
                )
                
                session.add(key_scope)
                print(f"✅ ADDED: {scope_name}")
                added_count += 1
            
            # Commit changes
            session.commit()
            
            print()
            print("=" * 70)
            print(f"✅ Update completed!")
            print(f"   - Added: {added_count} scope(s)")
            print(f"   - Skipped: {skipped_count} scope(s)")
            print("=" * 70)
            
            # Display total scopes for admin key
            total_scopes = session.execute(
                select(AKMAPIKeyScope)
                .where(AKMAPIKeyScope.api_key_id == ADMIN_KEY_ID)
            ).scalars().all()
            
            print(f"\nTotal scopes for admin key: {len(total_scopes)}")
            
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating admin key scopes: {e}")
            print(f"❌ ERROR: {e}")
            return False


if __name__ == "__main__":
    print("=" * 70)
    print("UPDATE ADMIN API KEY WITH PROJECT CONFIGURATION SCOPES")
    print("=" * 70)
    print()
    
    success = update_admin_key_scopes()
    
    if success:
        print()
        print("🎉 Admin key updated successfully!")
        print()
        print("📌 You can now use the admin key to:")
        print("   - View project configurations: GET /akm/projects/{id}/configuration")
        print("   - Create/update configs: PUT /akm/projects/{id}/configuration")
        print("   - Delete configs: DELETE /akm/projects/{id}/configuration")
        exit(0)
    else:
        print()
        print("❌ Update failed! Check the errors above.")
        exit(1)
