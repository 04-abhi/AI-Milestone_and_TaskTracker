"""Notification service."""
from typing import List, Optional, Tuple

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import Notification, NotificationPriority, NotificationType
from app.schemas.notification import NotificationCreate


class NotificationService:

    @staticmethod
    async def create(db: AsyncSession, data: NotificationCreate) -> Notification:
        notif = Notification(**data.model_dump())
        db.add(notif)
        await db.flush()
        await db.refresh(notif)
        return notif

    @staticmethod
    async def create_notification(
        db: AsyncSession,
        user_id: int,
        title: str,
        message: str,
        notification_type: NotificationType,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[int] = None,
        action_url: Optional[str] = None,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=notification_type,
            priority=priority,
            related_entity_type=related_entity_type,
            related_entity_id=related_entity_id,
            action_url=action_url,
        )
        db.add(notif)
        await db.flush()
        await db.refresh(notif)
        return notif

    @staticmethod
    async def list_for_user(
        db: AsyncSession,
        user_id: int,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Notification], int]:
        query = select(Notification).where(Notification.user_id == user_id)
        if unread_only:
            query = query.where(Notification.is_read == False)  # noqa: E712

        total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
        notifs = (
            await db.scalars(query.order_by(Notification.created_at.desc()).offset(skip).limit(limit))
        ).all()
        return list(notifs), total

    @staticmethod
    async def mark_read(db: AsyncSession, notification_id: int, user_id: int) -> bool:
        notif = await db.scalar(
            select(Notification).where(
                Notification.id == notification_id, Notification.user_id == user_id
            )
        )
        if notif:
            notif.is_read = True
            await db.flush()
            return True
        return False

    @staticmethod
    async def mark_all_read(db: AsyncSession, user_id: int) -> int:
        result = await db.execute(
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)  # noqa: E712
            .values(is_read=True)
        )
        return result.rowcount

    @staticmethod
    async def delete_notification(db: AsyncSession, notification_id: int, user_id: int) -> bool:
        notif = await db.scalar(
            select(Notification).where(
                Notification.id == notification_id, Notification.user_id == user_id
            )
        )
        if notif:
            await db.delete(notif)
            await db.flush()
            return True
        return False

    @staticmethod
    async def get_unread_count(db: AsyncSession, user_id: int) -> int:
        return await db.scalar(
            select(func.count(Notification.id)).where(
                Notification.user_id == user_id, Notification.is_read == False  # noqa: E712
            )
        ) or 0
