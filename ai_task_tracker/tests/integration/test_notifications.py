"""Integration tests – Notification endpoints."""
import pytest
from httpx import AsyncClient

from app.models.notification import NotificationType, NotificationPriority


@pytest.mark.asyncio
async def test_list_notifications_empty(client: AsyncClient, auth_headers):
    resp = await client.get("/api/v1/notifications", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json()["data"], list)


@pytest.mark.asyncio
async def test_unread_count(client: AsyncClient, auth_headers):
    resp = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert resp.status_code == 200
    assert "count" in resp.json()["data"]


@pytest.mark.asyncio
async def test_mark_all_read(client: AsyncClient, auth_headers, test_user, db):
    from app.models.notification import Notification
    for i in range(3):
        n = Notification(
            user_id=test_user.id,
            title=f"Notif {i}",
            message="Test message",
            notification_type=NotificationType.SYSTEM,
            priority=NotificationPriority.LOW,
        )
        db.add(n)
    await db.flush()

    resp = await client.post("/api/v1/notifications/mark-all-read", headers=auth_headers)
    assert resp.status_code == 200

    count_resp = await client.get("/api/v1/notifications/unread-count", headers=auth_headers)
    assert count_resp.json()["data"]["count"] == 0
