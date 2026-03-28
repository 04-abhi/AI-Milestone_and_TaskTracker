"""Integration tests – Task endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_task(client: AsyncClient, auth_headers):
    resp = await client.post(
        "/api/v1/tasks",
        json={"title": "My First Task", "priority": "high", "category": "work"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "My First Task"
    assert data["priority"] == "high"
    assert data["status"] == "todo"


@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient, auth_headers, test_task):
    resp = await client.get("/api/v1/tasks", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
    assert body["meta"]["total"] >= 1


@pytest.mark.asyncio
async def test_get_task(client: AsyncClient, auth_headers, test_task):
    resp = await client.get(f"/api/v1/tasks/{test_task.id}", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == test_task.id


@pytest.mark.asyncio
async def test_get_task_not_found(client: AsyncClient, auth_headers):
    resp = await client.get("/api/v1/tasks/99999", headers=auth_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_task(client: AsyncClient, auth_headers, test_task):
    resp = await client.patch(
        f"/api/v1/tasks/{test_task.id}",
        json={"title": "Updated Title", "priority": "urgent"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "Updated Title"
    assert resp.json()["priority"] == "urgent"


@pytest.mark.asyncio
async def test_update_task_status(client: AsyncClient, auth_headers, test_task):
    resp = await client.patch(
        f"/api/v1/tasks/{test_task.id}/status",
        json={"status": "in_progress"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "in_progress"


@pytest.mark.asyncio
async def test_complete_task_sets_completed_at(client: AsyncClient, auth_headers, test_task):
    resp = await client.patch(
        f"/api/v1/tasks/{test_task.id}/status",
        json={"status": "completed"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["completed_at"] is not None


@pytest.mark.asyncio
async def test_filter_tasks_by_status(client: AsyncClient, auth_headers, test_task):
    resp = await client.get("/api/v1/tasks?status=todo", headers=auth_headers)
    assert resp.status_code == 200
    for task in resp.json()["data"]:
        assert task["status"] == "todo"


@pytest.mark.asyncio
async def test_search_tasks(client: AsyncClient, auth_headers, test_task):
    resp = await client.get("/api/v1/tasks?search=Test", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["meta"]["total"] >= 1


@pytest.mark.asyncio
async def test_delete_task(client: AsyncClient, auth_headers):
    create_resp = await client.post(
        "/api/v1/tasks",
        json={"title": "Task to Delete"},
        headers=auth_headers,
    )
    task_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert del_resp.status_code == 200

    get_resp = await client.get(f"/api/v1/tasks/{task_id}", headers=auth_headers)
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_bulk_delete_tasks(client: AsyncClient, auth_headers):
    ids = []
    for i in range(3):
        r = await client.post(
            "/api/v1/tasks", json={"title": f"Bulk Task {i}"}, headers=auth_headers
        )
        ids.append(r.json()["id"])

    resp = await client.post(
        "/api/v1/tasks/bulk-delete", json={"task_ids": ids}, headers=auth_headers
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_cannot_access_other_users_task(client: AsyncClient, auth_headers, admin_user, db):
    """User should not be able to see tasks belonging to another user."""
    from app.models.task import Task, TaskStatus, TaskPriority, TaskCategory
    other_task = Task(
        user_id=admin_user.id,
        title="Admin's private task",
        status=TaskStatus.TODO,
        priority=TaskPriority.LOW,
        category=TaskCategory.WORK,
    )
    db.add(other_task)
    await db.flush()

    resp = await client.get(f"/api/v1/tasks/{other_task.id}", headers=auth_headers)
    assert resp.status_code == 404
