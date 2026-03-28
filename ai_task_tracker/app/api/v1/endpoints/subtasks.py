"""Subtask endpoints."""
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id, get_db
from app.schemas.common import SuccessResponse
from app.schemas.subtask import SubtaskCreate, SubtaskReorder, SubtaskResponse, SubtaskUpdate
from app.services.subtask_service import SubtaskService
from app.services.task_service import TaskService

router = APIRouter(prefix="/tasks/{task_id}/subtasks", tags=["Subtasks"])


@router.post("", response_model=SubtaskResponse, status_code=status.HTTP_201_CREATED)
async def create_subtask(
    task_id: int,
    data: SubtaskCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a subtask under a task."""
    task = await TaskService.get_or_raise(db, task_id, user_id)
    return await SubtaskService.create(db, task, data)


@router.get("", response_model=List[SubtaskResponse])
async def list_subtasks(
    task_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all subtasks for a task."""
    await TaskService.get_or_raise(db, task_id, user_id)
    return await SubtaskService.list_by_task(db, task_id)


@router.patch("/{subtask_id}", response_model=SubtaskResponse)
async def update_subtask(
    task_id: int,
    subtask_id: int,
    data: SubtaskUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a subtask."""
    await TaskService.get_or_raise(db, task_id, user_id)
    subtask = await SubtaskService.get_or_raise(db, subtask_id, task_id)
    return await SubtaskService.update(db, subtask, data)


@router.delete("/{subtask_id}", response_model=SuccessResponse)
async def delete_subtask(
    task_id: int,
    subtask_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Delete a subtask."""
    await TaskService.get_or_raise(db, task_id, user_id)
    subtask = await SubtaskService.get_or_raise(db, subtask_id, task_id)
    await SubtaskService.delete(db, subtask)
    return SuccessResponse(message="Subtask deleted")


@router.post("/reorder", response_model=SuccessResponse)
async def reorder_subtasks(
    task_id: int,
    data: SubtaskReorder,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Reorder subtasks by providing a sorted list of IDs."""
    await TaskService.get_or_raise(db, task_id, user_id)
    await SubtaskService.reorder(db, task_id, data.subtask_ids)
    return SuccessResponse(message="Subtasks reordered")
