"""Integration tests – Admin endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_list_users(client: AsyncClient, admin_headers, test_user):
    resp = await client.get("/api/v1/admin/users", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] >= 1


@pytest.mark.asyncio
async def test_non_admin_cannot_access_admin_routes(client: AsyncClient, auth_headers):
    resp = await client.get("/api/v1/admin/users", headers=auth_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_system_stats(client: AsyncClient, admin_headers):
    resp = await client.get("/api/v1/admin/stats", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "users" in data
    assert "tasks" in data


@pytest.mark.asyncio
async def test_admin_update_user(client: AsyncClient, admin_headers, test_user):
    resp = await client.patch(
        f"/api/v1/admin/users/{test_user.id}",
        json={"is_verified": True},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["is_verified"] is True


@pytest.mark.asyncio
async def test_admin_get_nonexistent_user(client: AsyncClient, admin_headers):
    resp = await client.get("/api/v1/admin/users/99999", headers=admin_headers)
    assert resp.status_code == 404
