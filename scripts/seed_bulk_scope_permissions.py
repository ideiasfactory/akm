"""
Seed new scopes permissions for bulk operations
"""
from src.database.connection import get_session
from src.database.models import AKMAPIKey
from src.database.repositories.scope_repository import scope_repository
from src.database.repositories.project_repository import project_repository

async def seed_bulk_scope_permissions(session):
    # Bulk operation scopes
    bulk_scopes = [
        {"scope_name": "akm:scopes:bulk:*", "description": "Bulk operations on scopes"},
        {"scope_name": "akm:scopes:bulk:json", "description": "Bulk upsert scopes via JSON"},
        {"scope_name": "akm:scopes:bulk:file", "description": "Bulk upsert scopes via file upload"},
    ]
    for scope in bulk_scopes:
        await scope_repository.create(
            session,
            project_id=1,  # Adjust project_id as needed
            scope_name=scope["scope_name"],
            description=scope["description"]
        )

# Usage example (run in migration or script):
# import asyncio
# session = get_session()
# asyncio.run(seed_bulk_scope_permissions(session))
