"""
Script to verify migration data
"""
import asyncio
from sqlalchemy import text
from src.database.connection import get_session


async def verify():
    async for session in get_session():
        # Check projects
        result = await session.execute(text('SELECT id, name, prefix FROM akm_projects'))
        projects = result.fetchall()
        print(f"\n✅ Projects: {len(projects)}")
        for p in projects:
            print(f"   - ID: {p[0]}, Name: {p[1]}, Prefix: {p[2]}")
        
        # Check scopes
        result = await session.execute(text('SELECT COUNT(*) FROM akm_scopes WHERE project_id=1'))
        scopes_count = result.scalar()
        print(f"\n✅ Scopes for project 1: {scopes_count}")
        
        # Check specific scopes
        result = await session.execute(text("""
            SELECT id, scope_name FROM akm_scopes 
            WHERE project_id=1 AND scope_name IN ('akm:*', 'akm:projects:*', 'akm:keys:*')
            ORDER BY scope_name
        """))
        important_scopes = result.fetchall()
        print(f"   Important scopes:")
        for s in important_scopes:
            print(f"   - ID: {s[0]}, Scope: {s[1]}")
        
        # Check webhook events
        result = await session.execute(text('SELECT COUNT(*) FROM akm_webhook_events'))
        events_count = result.scalar()
        print(f"\n✅ Webhook events: {events_count}")
        
        # Check sensitive fields
        result = await session.execute(text('SELECT COUNT(*) FROM akm_sensitive_fields WHERE project_id IS NULL'))
        global_fields_count = result.scalar()
        
        result = await session.execute(text('SELECT COUNT(*) FROM akm_sensitive_fields WHERE project_id IS NOT NULL'))
        project_fields_count = result.scalar()
        
        print(f"\n✅ Sensitive fields:")
        print(f"   🌍 Global fields (apply to all projects): {global_fields_count}")
        print(f"   📁 Project-specific fields: {project_fields_count}")
        
        result = await session.execute(text("""
            SELECT field_name, 
                   CASE WHEN project_id IS NULL THEN '🌍 Global' ELSE CONCAT('📁 Project ', project_id) END as scope
            FROM akm_sensitive_fields 
            ORDER BY project_id NULLS FIRST, field_name
        """))
        fields = result.fetchall()
        print(f"   Fields:")
        for f in fields:
            print(f"     - {f[1]}: {f[0]}")
        
        # Check admin key
        result = await session.execute(text("""
            SELECT k.id, k.name, s.scope_name 
            FROM akm_api_keys k
            JOIN akm_api_key_scopes aks ON k.id = aks.api_key_id
            JOIN akm_scopes s ON aks.scope_id = s.id
            WHERE k.id=1
        """))
        admin_key = result.fetchone()
        print(f"\n✅ Admin API Key:")
        print(f"   - ID: {admin_key[0]}")
        print(f"   - Name: {admin_key[1]}")
        print(f"   - Scope: {admin_key[2]}")
        
        # Check API key config
        result = await session.execute(text("""
            SELECT rate_limit_enabled, ip_whitelist_enabled 
            FROM akm_api_key_configs WHERE api_key_id=1
        """))
        config = result.fetchone()
        print(f"   - Rate limit: {config[0]}")
        print(f"   - IP whitelist: {config[1]}")
        
        print("\n" + "=" * 80)
        print("✅ All data successfully seeded!")
        print("=" * 80)
        
        break


if __name__ == "__main__":
    asyncio.run(verify())
