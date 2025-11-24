import pytest
import json
from httpx import AsyncClient
from main import app  # If 'main.py' is in the project root, or adjust the import path as needed

@pytest.mark.asyncio
async def test_bulk_delete_all_scopes_success(test_db, test_project, test_api_key):
    async with AsyncClient(base_url="http://test") as ac:
        # Insert some scopes for the project first (setup)
        # ...existing code to insert scopes...
        response = await ac.delete(
            "/scopes/delete-all",
            json={"project_id": test_project.id, "confirm": "delete all scopes"},
            headers={"X-API-Key": test_api_key}
        )
        assert response.status_code == 204

@pytest.mark.asyncio
async def test_bulk_delete_all_scopes_bad_confirm(test_db, test_project, test_api_key):
    async with AsyncClient(base_url="http://test") as ac:
        response = await ac.delete(
            "/scopes/delete-all",
            content=json.dumps({"project_id": test_project.id, "confirm": "wrong confirm"}),
            headers={"X-API-Key": test_api_key, "Content-Type": "application/json"}
        )
        assert response.status_code == 400
        assert "Confirmation string" in response.text

@pytest.mark.asyncio
async def test_bulk_delete_all_scopes_not_found(test_db, test_api_key):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.delete(
            "/scopes/delete-all",
            content=json.dumps({"project_id": 99999, "confirm": "delete all scopes"}),
            headers={"X-API-Key": test_api_key, "Content-Type": "application/json"}
        )
        assert response.status_code == 404
        assert "not found" in response.text
