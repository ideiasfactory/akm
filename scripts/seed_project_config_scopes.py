"""
Seed script to import new project configuration scopes for AKM (project_id=1).

This script adds the new scopes for dynamic project configuration:
- akm:projects:config:read
- akm:projects:config:write
- akm:projects:config:delete
- akm:projects:config:*

Usage:
    python scripts/seed_project_config_scopes.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import datetime

from src.database.connection import get_engine
from src.database.models import AKMScope, AKMProject
from src.logging_config import get_logger
from sqlalchemy import select
from sqlalchemy.orm import Session

logger = get_logger(__name__)

# Project configuration scopes to add
NEW_SCOPES = [
    {
        "scope_name": "akm:projects:config:read",
        "description": "View project dynamic configurations (CORS, rate limits, IP allowlist)",
        "is_active": True
    },
    {
        "scope_name": "akm:projects:config:write",
        "description": "Create and update project dynamic configurations",
        "is_active": True
    },
    {
        "scope_name": "akm:projects:config:delete",
        "description": "Delete project configurations (reset to defaults)",
        "is_active": True
    },
    {
        "scope_name": "akm:projects:config:*",
        "description": "Full project configuration management",
        "is_active": True
    }
]

AKM_PROJECT_ID = 1


def seed_project_config_scopes():
    """
    Seed new project configuration scopes for AKM project.
    """
    engine = get_engine()
    
    with Session(engine) as session:
        try:
            # Verify AKM project exists
            project = session.execute(
                select(AKMProject).where(AKMProject.id == AKM_PROJECT_ID)
            ).scalar_one_or_none()
            
            if not project:
                logger.error(f"AKM Project with ID {AKM_PROJECT_ID} not found!")
                print(f"❌ ERROR: AKM Project with ID {AKM_PROJECT_ID} not found!")
                return False
            
            print(f"✅ Found AKM Project: {project.name} (ID: {project.id}, Prefix: {project.prefix})")
            print()
            
            added_count = 0
            skipped_count = 0
            
            for scope_data in NEW_SCOPES:
                # Check if scope already exists
                existing_scope = session.execute(
                    select(AKMScope).where(
                        AKMScope.project_id == AKM_PROJECT_ID,
                        AKMScope.scope_name == scope_data["scope_name"]
                    )
                ).scalar_one_or_none()
                
                if existing_scope:
                    print(f"⏭️  SKIPPED: {scope_data['scope_name']} (already exists)")
                    skipped_count += 1
                    continue
                
                # Create new scope
                new_scope = AKMScope(
                    project_id=AKM_PROJECT_ID,
                    scope_name=scope_data["scope_name"],
                    description=scope_data["description"],
                    is_active=scope_data["is_active"],
                    created_at=datetime.utcnow()
                )
                
                session.add(new_scope)
                print(f"✅ ADDED: {scope_data['scope_name']}")
                print(f"   Description: {scope_data['description']}")
                print()
                added_count += 1
            
            # Commit all changes
            session.commit()
            
            print("=" * 70)
            print(f"✅ Seed completed successfully!")
            print(f"   - Added: {added_count} scope(s)")
            print(f"   - Skipped: {skipped_count} scope(s)")
            print("=" * 70)
            
            # Display total scopes for AKM project
            total_scopes = session.execute(
                select(AKMScope).where(AKMScope.project_id == AKM_PROJECT_ID)
            ).scalars().all()
            
            print(f"\nTotal scopes for AKM project: {len(total_scopes)}")
            
            return True
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error seeding scopes: {e}")
            print(f"❌ ERROR: {e}")
            return False


def verify_scopes_json():
    """
    Verify that scopes.json has been updated.
    """
    scopes_file = Path(__file__).parent.parent / "data" / "scopes.json"
    
    if not scopes_file.exists():
        print(f"⚠️  WARNING: {scopes_file} not found")
        return False
    
    with open(scopes_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    version = data.get("version", "unknown")
    scopes = data.get("scopes", [])
    
    config_scopes = [s for s in scopes if "projects:config" in s.get("scope_name", "")]
    
    print(f"📄 scopes.json version: {version}")
    print(f"   Total scopes in file: {len(scopes)}")
    print(f"   Project config scopes: {len(config_scopes)}")
    
    if len(config_scopes) >= 4:
        print("   ✅ Project configuration scopes found in scopes.json")
        return True
    else:
        print("   ⚠️  WARNING: Project configuration scopes not found in scopes.json")
        print("   Please update data/scopes.json first!")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("SEED PROJECT CONFIGURATION SCOPES FOR AKM")
    print("=" * 70)
    print()
    
    # Verify scopes.json
    if not verify_scopes_json():
        print()
        print("❌ Please update data/scopes.json with the new scopes first!")
        print("   The file should include:")
        for scope in NEW_SCOPES:
            print(f"   - {scope['scope_name']}")
        exit(1)
    
    print()
    print("=" * 70)
    print("IMPORTING SCOPES TO DATABASE")
    print("=" * 70)
    print()
    
    success = seed_project_config_scopes()
    
    if success:
        print()
        print("🎉 All done! Project configuration scopes are now available.")
        print()
        print("📌 Next steps:")
        print("   1. Update existing admin API keys to include new scopes")
        print("   2. Test the new endpoints:")
        print("      - PUT /akm/projects/{id}/configuration")
        print("      - GET /akm/projects/{id}/configuration")
        print("      - DELETE /akm/projects/{id}/configuration")
        exit(0)
    else:
        print()
        print("❌ Seed failed! Check the errors above.")
        exit(1)
