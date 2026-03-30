from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.push import PushSubscriptionIn
from app.services.push_service import (
    delete_subscription, save_subscription, send_push_to_user
)

router = APIRouter(prefix="/push", tags=["Push Notifications"])


@router.get("/vapid-key")
async def get_vapid_key():
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(
            status_code=503,
            detail="Push notifications not configured. Run: python scripts/generate_vapid.py"
        )
    return {"public_key": settings.VAPID_PUBLIC_KEY}


@router.post("/subscribe")
async def subscribe(
    data: PushSubscriptionIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await save_subscription(db, current_user.id, data.endpoint, data.p256dh, data.auth)
    return {"message": "Subscribed to push notifications"}


# ── FIX: Changed DELETE → POST /unsubscribe ──────────────────────────────────
# HTTP DELETE with a request body is technically allowed but many HTTP clients
# (browsers, proxies, FastAPI's test client) silently drop the body, causing
# 422 Unprocessable Entity because the required JSON fields never arrive.
# Using POST /unsubscribe is the standard workaround used by Firebase, OneSignal, etc.
@router.post("/unsubscribe")
async def unsubscribe(
    data: PushSubscriptionIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await delete_subscription(db, data.endpoint)
    return {"message": "Unsubscribed"}


@router.post("/test")
async def test_push(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sent = await send_push_to_user(
        db, current_user.id,
        title="🔔 Test Notification",
        body="Push notifications are working on your device!",
        url="/",
    )
    if sent == 0:
        raise HTTPException(
            status_code=400,
            detail=(
                "No subscriptions found, or VAPID not configured. "
                "Enable notifications in Settings first."
            ),
        )
    return {"message": f"Notification sent to {sent} device(s)"}
