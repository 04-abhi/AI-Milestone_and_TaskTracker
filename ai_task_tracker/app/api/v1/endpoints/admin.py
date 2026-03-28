"""Admin panel endpoints – requires is_admin = True."""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_admin_user, get_db
from app.models.task import Task
from app.models.user import User
from app.schemas.common import PaginatedResponse, PaginationMeta, SuccessResponse
from app.schemas.user import AdminUserUpdate, UserResponse
from app.services.user_service import UserService

router = APIRouter(prefix="/admin", tags=["Admin"])


# ── User Management ────────────────────────────────────────────────────────────

@router.get("/users", response_model=PaginatedResponse[UserResponse])
async def admin_list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(25, ge=1, le=100),
    _admin=Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """List all users (admin only)."""
    skip = (page - 1) * per_page
    users, total = await UserService.list_all(db, skip=skip, limit=per_page)
    total_pages = max(1, -(-total // per_page))
    return {
        "success": True,
        "data": users,
        "meta": PaginationMeta(
            total=total, page=page, per_page=per_page,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    }


@router.get("/users/{user_id}", response_model=UserResponse)
async def admin_get_user(
    user_id: int,
    _admin=Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Get any user by ID (admin only)."""
    from app.core.exceptions import NotFoundError
    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise NotFoundError("User")
    return user


@router.patch("/users/{user_id}", response_model=UserResponse)
async def admin_update_user(
    user_id: int,
    data: AdminUserUpdate,
    _admin=Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Update is_active / is_admin / is_verified for any user (admin only)."""
    from app.core.exceptions import NotFoundError
    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise NotFoundError("User")
    return await UserService.admin_update(db, user, data)


@router.delete("/users/{user_id}", response_model=SuccessResponse)
async def admin_delete_user(
    user_id: int,
    _admin=Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete any user (admin only)."""
    from app.core.exceptions import NotFoundError
    user = await UserService.get_by_id(db, user_id)
    if not user:
        raise NotFoundError("User")
    await UserService.soft_delete(db, user)
    return SuccessResponse(message="User deleted")


# ── System Stats ───────────────────────────────────────────────────────────────

@router.get("/stats")
async def admin_system_stats(
    _admin=Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """High-level system statistics (admin only)."""
    total_users = await db.scalar(select(func.count(User.id)).where(User.deleted_at.is_(None))) or 0
    active_users = await db.scalar(
        select(func.count(User.id)).where(User.is_active == True, User.deleted_at.is_(None))  # noqa: E712
    ) or 0
    admin_users = await db.scalar(
        select(func.count(User.id)).where(User.is_admin == True, User.deleted_at.is_(None))  # noqa: E712
    ) or 0
    total_tasks = await db.scalar(select(func.count(Task.id)).where(Task.deleted_at.is_(None))) or 0

    from app.models.task import TaskStatus
    completed_tasks = await db.scalar(
        select(func.count(Task.id)).where(
            Task.status == TaskStatus.COMPLETED, Task.deleted_at.is_(None)
        )
    ) or 0

    from app.models.milestone import Milestone
    total_milestones = await db.scalar(
        select(func.count(Milestone.id)).where(Milestone.deleted_at.is_(None))
    ) or 0

    from app.models.ai_suggestion import AISuggestion
    total_suggestions = await db.scalar(select(func.count(AISuggestion.id))) or 0

    return {
        "success": True,
        "data": {
            "users": {
                "total": total_users,
                "active": active_users,
                "admins": admin_users,
            },
            "tasks": {
                "total": total_tasks,
                "completed": completed_tasks,
                "completion_rate": round(completed_tasks / max(total_tasks, 1), 4),
            },
            "milestones": {"total": total_milestones},
            "ai_suggestions": {"total": total_suggestions},
        },
    }
