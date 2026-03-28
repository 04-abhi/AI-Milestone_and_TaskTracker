"""Notification Pydantic schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.notification import NotificationPriority, NotificationType


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    notification_type: NotificationType
    priority: NotificationPriority
    related_entity_type: Optional[str]
    related_entity_id: Optional[int]
    is_read: bool
    action_url: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationUpdate(BaseModel):
    is_read: bool = True


class NotificationBulkRead(BaseModel):
    notification_ids: list[int]


class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    action_url: Optional[str] = None
