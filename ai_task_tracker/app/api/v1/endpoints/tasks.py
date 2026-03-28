"""Task endpoints."""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id, get_db
from app.schemas.common import PaginatedResponse, PaginationMeta, SuccessResponse
from app.schemas.task import (
    TaskBulkDelete,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks", tags=["Tasks"])


def _make_paginated(items, total, page, per_page) -> dict:
    total_pages = max(1, -(-total // per_page))
    return {
        "success": True,
        "data": items,
        "meta": PaginationMeta(
            total=total,
            page=page,
            per_page=per_page,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    }


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    data: TaskCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new task."""
    task = await TaskService.create(db, user_id, data)
    return task


@router.get("", response_model=PaginatedResponse[TaskListResponse])
async def list_tasks(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    milestone_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None, max_length=100),
    is_pinned: Optional[bool] = Query(None),
    due_date_from: Optional[datetime] = Query(None),
    due_date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List tasks with filtering and pagination."""
    skip = (page - 1) * per_page
    tasks, total = await TaskService.list_tasks(
        db,
        user_id=user_id,
        status=status,
        priority=priority,
        category=category,
        milestone_id=milestone_id,
        search=search,
        is_pinned=is_pinned,
        due_date_from=due_date_from,
        due_date_to=due_date_to,
        skip=skip,
        limit=per_page,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    task_list = []
    for t in tasks:
        total_sub = len([s for s in t.subtasks if not s.deleted_at]) if hasattr(t, 'subtasks') and t.subtasks else 0
        completed_sub = len([s for s in t.subtasks if not s.deleted_at and s.status.value == 'completed']) if hasattr(t, 'subtasks') and t.subtasks else 0
        task_list.append(TaskListResponse(
            id=t.id, user_id=t.user_id, milestone_id=t.milestone_id,
            title=t.title, status=t.status, priority=t.priority,
            category=t.category, tags=t.tags, due_date=t.due_date,
            progress_percentage=t.progress_percentage, is_pinned=t.is_pinned,
            subtask_count=total_sub, completed_subtask_count=completed_sub,
            created_at=t.created_at, updated_at=t.updated_at,
        ))

    return _make_paginated(task_list, total, page, per_page)


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a single task with its subtasks."""
    return await TaskService.get_or_raise(db, task_id, user_id)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    data: TaskUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a task."""
    task = await TaskService.get_or_raise(db, task_id, user_id)
    return await TaskService.update(db, task, data)


@router.patch("/{task_id}/status", response_model=TaskResponse)
async def update_task_status(
    task_id: int,
    data: TaskStatusUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Quickly update only the task status."""
    task = await TaskService.get_or_raise(db, task_id, user_id)
    return await TaskService.update(db, task, TaskUpdate(status=data.status))


@router.delete("/{task_id}", response_model=SuccessResponse)
async def delete_task(
    task_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a task."""
    task = await TaskService.get_or_raise(db, task_id, user_id)
    await TaskService.delete(db, task)
    return SuccessResponse(message="Task deleted")


@router.post("/bulk-delete", response_model=SuccessResponse)
async def bulk_delete_tasks(
    data: TaskBulkDelete,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple tasks at once."""
    count = await TaskService.bulk_delete(db, user_id, data.task_ids)
    return SuccessResponse(message=f"{count} task(s) deleted")
