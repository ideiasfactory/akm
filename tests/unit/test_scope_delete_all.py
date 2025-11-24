import pytest
from unittest.mock import AsyncMock
from src.database.repositories.scope_repository import ScopeRepository

@pytest.mark.asyncio
async def test_delete_all_by_project_deletes_all_scopes():
    session = AsyncMock()
    repo = ScopeRepository()
    # Simulate rowcount for deleted scopes
    session.execute.return_value.rowcount = 5
    deleted = await repo.delete_all_by_project(session, project_id=123)
    assert deleted == 5
    session.execute.assert_called()
    session.commit.assert_called()

@pytest.mark.asyncio
async def test_delete_all_by_project_no_scopes():
    session = AsyncMock()
    repo = ScopeRepository()
    session.execute.return_value.rowcount = 0
    deleted = await repo.delete_all_by_project(session, project_id=999)
    assert deleted == 0
    session.execute.assert_called()
    session.commit.assert_called()
