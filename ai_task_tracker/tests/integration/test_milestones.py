"""Integration tests – Milestone endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_milestone(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/milestones",
        json={
            "title": "Q3 Goals",
            "description": "All goals for Q3",
            "color": "#22c55e",
        },
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Q3 Goals"
    assert data["status"] == "planned"


@pytest.mark.asyncio
async def test_list_milestones(client: AsyncClient, auth_headers, test_milestone):
    resp = await client.get("/api/v1/milestones", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] >= 1


@pytest.mark.asyncio
async def test_get_milestone(client: AsyncClient, auth_headers, test_milestone):
    resp = await client.get(f"/api/v1/milestones/{test_milestone.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == test_milestone.id


@pytest.mark.asyncio
async def test_update_milestone(client: AsyncClient, auth_headers, test_milestone):
    resp = await client.patch(
        f"/api/v1/milestones/{test_milestone.id}",
        json={"title": "Updated Milestone", "color": "#ef4444"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Milestone"
    assert resp.json()["color"] == "#ef4444"


@pytest.mark.asyncio
async def test_delete_milestone(client: AsyncClient, auth_headers):
    create = await client.post(
        "/api/v1/milestones",
        json={"title": "To Delete"},
        headers=auth_headers,
    )
    mid = create.json()["id"]

    del_resp = await client.delete(f"/api/v1/milestones/{mid}", headers=auth_headers)
    assert del_resp.status_code == 200

    get_resp = await client.get(f"/api/v1/milestones/{mid}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_color_rejected(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/milestones",
        json={"title": "Bad Color", "color": "red"},  # not a valid hex
        headers=auth_headers,
    )
    assert resp.status_code == 422
