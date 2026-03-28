"""Notification endpoints."""
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id, get_db
from app.schemas.common import PaginatedResponse, PaginationMeta, SuccessResponse
from app.schemas.notification import NotificationBulkRead, NotificationResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=PaginatedResponse[NotificationResponse])
async def list_notifications(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List notifications for the current user."""
    skip = (page - 1) * per_page
    notifications, total = await NotificationService.list_for_user(
        db, user_id=user_id, unread_only=unread_only, skip=skip, limit=per_page
    )
    total_pages = max(1, -(-total // per_page))
    return {
        "success": True,
        "data": notifications,
        "meta": PaginationMeta(
            total=total, page=page, per_page=per_page,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    }


@router.get("/unread-count")
async def get_unread_count(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get total unread notification count."""
    count = await NotificationService.get_unread_count(db, user_id)
    return {"success": True, "data": {"count": count}}


@router.patch("/{notification_id}/read", response_model=SuccessResponse)
async def mark_read(
    notification_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark a single notification as read."""
    await NotificationService.mark_read(db, notification_id, user_id)
    return SuccessResponse(message="Notification marked as read")


@router.post("/mark-all-read", response_model=SuccessResponse)
async def mark_all_read(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark all notifications as read."""
    count = await NotificationService.mark_all_read(db, user_id)
    return SuccessResponse(message=f"{count} notification(s) marked as read")


@router.delete("/{notification_id}", response_model=SuccessResponse)
async def delete_notification(
    notification_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a notification."""
    await NotificationService.delete_notification(db, notification_id, user_id)
    return SuccessResponse(message="Notification deleted")
