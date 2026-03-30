import json
import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.push_subscription import PushSubscription
from app.core.config import settings

logger = logging.getLogger(__name__)


async def save_subscription(
    db: AsyncSession, user_id: int, endpoint: str, p256dh: str, auth: str
) -> PushSubscription:
    existing = await db.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )
    if existing:
        existing.user_id = user_id
        existing.p256dh  = p256dh
        existing.auth    = auth
        await db.flush()
        return existing

    sub = PushSubscription(user_id=user_id, endpoint=endpoint, p256dh=p256dh, auth=auth)
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    return sub


async def delete_subscription(db: AsyncSession, endpoint: str) -> None:
    sub = await db.scalar(
        select(PushSubscription).where(PushSubscription.endpoint == endpoint)
    )
    if sub:
        await db.delete(sub)
        await db.flush()


async def send_push_to_user(
    db: AsyncSession, user_id: int, title: str, body: str, url: str = "/"
) -> int:
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        logger.warning("VAPID keys not configured — push notifications disabled")
        return 0

    subs = (
        await db.scalars(
            select(PushSubscription).where(PushSubscription.user_id == user_id)
        )
    ).all()

    if not subs:
        return 0

    sent  = 0
    stale = []
    for sub in subs:
        ok = await _send_one(sub, title, body, url)
        if ok:
            sent += 1
        else:
            stale.append(sub)

    for sub in stale:
        await db.delete(sub)
    if stale:
        await db.flush()

    return sent


async def _send_one(sub: PushSubscription, title: str, body: str, url: str) -> bool:
    """
    pywebpush 2.0.0 ships with py-vapid and aiohttp.
    The webpush() function signature in 2.0.0 is:

        webpush(
            subscription_info,
            data,
            vapid_private_key,   # <-- raw base64url string OR path to PEM file
            vapid_claims,        # <-- dict {"sub": "mailto:..."}
            content_encoding,
            requests_session,
            ttl,
            timeout,
            curl,
            verbose,
            auth,
        )

    It is still synchronous in 2.0.0 (aiohttp is used internally only
    for the async variant webpush_async). We run it in a thread executor
    so it doesn't block FastAPI's event loop.
    """
    import asyncio
    import functools

    loop = asyncio.get_event_loop()
    ok   = await loop.run_in_executor(None, functools.partial(_send_sync, sub, title, body, url))
    return ok


def _send_sync(sub: PushSubscription, title: str, body: str, url: str) -> bool:
    """Synchronous push — called from a thread pool to avoid blocking the event loop."""
    try:
        from pywebpush import webpush, WebPushException

        payload = json.dumps({"title": title, "body": body, "url": url})

        webpush(
            subscription_info={
                "endpoint": sub.endpoint,
                "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
            },
            data=payload,
            vapid_private_key=settings.VAPID_PRIVATE_KEY.strip(),
            vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}"},
        )
        return True

    except Exception as e:
        logger.warning(f"Push failed for sub {sub.id}: {e}")
        return False
