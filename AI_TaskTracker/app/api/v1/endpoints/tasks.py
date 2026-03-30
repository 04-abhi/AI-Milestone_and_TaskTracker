import math
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.task import (
    TaskCreate, TaskListOut, TaskOut, TaskUpdate,
    SubtaskCreate, SubtaskUpdate, SubtaskOut,
)
from app.services.task_service import (
    create_task, delete_task, get_task, list_tasks, update_task,
    archive_task, get_subtasks, create_subtask, get_subtask,
    update_subtask, delete_subtask,
)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


# ── Tasks ──────────────────────────────────────────────────

@router.post("", response_model=TaskOut, status_code=201)
async def create(
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await create_task(db, current_user.id, data)
    task.__dict__["subtasks"] = []
    return task


@router.get("", response_model=TaskListOut)
async def list_all(
    status:           Optional[str]  = Query(None),
    priority:         Optional[str]  = Query(None),
    search:           Optional[str]  = Query(None),
    tag:              Optional[str]  = Query(None),
    include_archived: bool           = Query(False),
    page:             int            = Query(1, ge=1),
    per_page:         int            = Query(20, ge=1, le=500),
    current_user:     User           = Depends(get_current_user),
    db:               AsyncSession   = Depends(get_db),
):
    tasks, total = await list_tasks(
        db, current_user.id,
        status=status, priority=priority,
        search=search, tag=tag,
        include_archived=include_archived,
        page=page, per_page=per_page,
    )
    return TaskListOut(
        items=tasks,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=max(1, math.ceil(total / per_page)),
    )


@router.get("/{task_id}", response_model=TaskOut)
async def get_one(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.__dict__["subtasks"] = await get_subtasks(db, task_id)
    return task


@router.patch("/{task_id}", response_model=TaskOut)
async def update_one(
    task_id: int,
    data: TaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task = await update_task(db, task, data)
    task.__dict__["subtasks"] = await get_subtasks(db, task_id)
    return task


@router.post("/{task_id}/archive", response_model=TaskOut)
async def archive_one(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task = await archive_task(db, task)
    task.__dict__["subtasks"] = await get_subtasks(db, task_id)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_one(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await delete_task(db, task)


# ── Subtasks ───────────────────────────────────────────────

@router.get("/{task_id}/subtasks", response_model=list[SubtaskOut])
async def list_subtasks(
    task_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return await get_subtasks(db, task_id)


@router.post("/{task_id}/subtasks", response_model=SubtaskOut, status_code=201)
async def add_subtask(
    task_id: int,
    data: SubtaskCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await get_task(db, task_id, current_user.id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return await create_subtask(db, task_id, current_user.id, data)


@router.patch("/{task_id}/subtasks/{subtask_id}", response_model=SubtaskOut)
async def update_one_subtask(
    task_id: int,
    subtask_id: int,
    data: SubtaskUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await get_subtask(db, subtask_id, current_user.id)
    if not sub or sub.task_id != task_id:
        raise HTTPException(status_code=404, detail="Subtask not found")
    return await update_subtask(db, sub, data)


@router.delete("/{task_id}/subtasks/{subtask_id}", status_code=204)
async def delete_one_subtask(
    task_id: int,
    subtask_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    sub = await get_subtask(db, subtask_id, current_user.id)
    if not sub or sub.task_id != task_id:
        raise HTTPException(status_code=404, detail="Subtask not found")
    await delete_subtask(db, sub)
