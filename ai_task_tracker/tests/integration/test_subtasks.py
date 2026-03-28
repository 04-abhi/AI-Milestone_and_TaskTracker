"""Integration tests – Subtask endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_subtask(client: AsyncClient, auth_headers, test_task):
    resp = await client.post(
        f"/api/v1/tasks/{test_task.id}/subtasks",
        json={"title": "Step 1", "estimated_minutes": 30},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Step 1"
    assert data["status"] == "todo"


@pytest.mark.asyncio
async def test_list_subtasks(client: AsyncClient, auth_headers, test_task):
    # create two subtasks first
    for i in range(2):
        await client.post(
            f"/api/v1/tasks/{test_task.id}/subtasks",
            json={"title": f"Sub {i}"},
            headers=auth_headers,
        )
    resp = await client.get(f"/api/v1/tasks/{test_task.id}/subtasks", headers=auth_headers)
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_complete_subtask_updates_task_progress(
    client: AsyncClient, auth_headers, test_task
):
    # create 2 subtasks
    ids = []
    for i in range(2):
        r = await client.post(
            f"/api/v1/tasks/{test_task.id}/subtasks",
            json={"title": f"Sub {i}"},
            headers=auth_headers,
        )
        ids.append(r.json()["id"])

    # complete first subtask
    await client.patch(
        f"/api/v1/tasks/{test_task.id}/subtasks/{ids[0]}",
        json={"status": "completed"},
        headers=auth_headers,
    )

    # task progress should be 50%
    task_resp = await client.get(f"/api/v1/tasks/{test_task.id}", headers=auth_headers)
    assert task_resp.json()["progress_percentage"] == 50


@pytest.mark.asyncio
async def test_delete_subtask(client: AsyncClient, auth_headers, test_task):
    create = await client.post(
        f"/api/v1/tasks/{test_task.id}/subtasks",
        json={"title": "To Remove"},
        headers=auth_headers,
    )
    sub_id = create.json()["id"]

    del_resp = await client.delete(
        f"/api/v1/tasks/{test_task.id}/subtasks/{sub_id}",
        headers=auth_headers,
    )
    assert del_resp.status_code == 200


@pytest.mark.asyncio
async def test_reorder_subtasks(client: AsyncClient, auth_headers, test_task):
    ids = []
    for i in range(3):
        r = await client.post(
            f"/api/v1/tasks/{test_task.id}/subtasks",
            json={"title": f"Sub {i}", "order_index": i},
            headers=auth_headers,
        )
        ids.append(r.json()["id"])

    reversed_ids = list(reversed(ids))
    resp = await client.post(
        f"/api/v1/tasks/{test_task.id}/subtasks/reorder",
        json={"subtask_ids": reversed_ids},
        headers=auth_headers,
    )
    assert resp.status_code == 200
