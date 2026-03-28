"""Subtask service."""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.subtask import Subtask, SubtaskStatus
from app.models.task import Task
from app.schemas.subtask import SubtaskCreate, SubtaskUpdate


class SubtaskService:

    @staticmethod
    async def create(db: AsyncSession, task: Task, data: SubtaskCreate) -> Subtask:
        subtask = Subtask(
            task_id=task.id,
            title=data.title,
            description=data.description,
            due_date=data.due_date,
            estimated_minutes=data.estimated_minutes,
            order_index=data.order_index,
        )
        db.add(subtask)
        await db.flush()
        await db.refresh(subtask)

        # Recalculate parent task progress
        await SubtaskService._update_task_progress(db, task.id)
        return subtask

    @staticmethod
    async def get_by_id(db: AsyncSession, subtask_id: int, task_id: int) -> Optional[Subtask]:
        return await db.scalar(
            select(Subtask).where(
                Subtask.id == subtask_id,
                Subtask.task_id == task_id,
                Subtask.deleted_at.is_(None),
            )
        )

    @staticmethod
    async def get_or_raise(db: AsyncSession, subtask_id: int, task_id: int) -> Subtask:
        subtask = await SubtaskService.get_by_id(db, subtask_id, task_id)
        if not subtask:
            raise NotFoundError("Subtask")
        return subtask

    @staticmethod
    async def list_by_task(db: AsyncSession, task_id: int) -> List[Subtask]:
        return list(
            (
                await db.scalars(
                    select(Subtask)
                    .where(Subtask.task_id == task_id, Subtask.deleted_at.is_(None))
                    .order_by(Subtask.order_index.asc(), Subtask.created_at.asc())
                )
            ).all()
        )

    @staticmethod
    async def update(db: AsyncSession, subtask: Subtask, data: SubtaskUpdate) -> Subtask:
        update_data = data.model_dump(exclude_unset=True)

        if "status" in update_data:
            new_status = update_data["status"]
            if new_status == SubtaskStatus.COMPLETED and not subtask.completed_at:
                subtask.completed_at = datetime.now(timezone.utc)
            elif new_status != SubtaskStatus.COMPLETED:
                subtask.completed_at = None

        for field, value in update_data.items():
            setattr(subtask, field, value)

        await db.flush()
        await db.refresh(subtask)
        await SubtaskService._update_task_progress(db, subtask.task_id)
        return subtask

    @staticmethod
    async def delete(db: AsyncSession, subtask: Subtask) -> None:
        task_id = subtask.task_id
        subtask.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        await SubtaskService._update_task_progress(db, task_id)

    @staticmethod
    async def reorder(db: AsyncSession, task_id: int, subtask_ids: List[int]) -> None:
        for idx, subtask_id in enumerate(subtask_ids):
            subtask = await SubtaskService.get_by_id(db, subtask_id, task_id)
            if subtask:
                subtask.order_index = idx
        await db.flush()

    @staticmethod
    async def _update_task_progress(db: AsyncSession, task_id: int) -> None:
        """Recalculate and save task progress based on subtask completion."""
        total = await db.scalar(
            select(func.count(Subtask.id)).where(
                Subtask.task_id == task_id, Subtask.deleted_at.is_(None)
            )
        )
        completed = await db.scalar(
            select(func.count(Subtask.id)).where(
                Subtask.task_id == task_id,
                Subtask.status == SubtaskStatus.COMPLETED,
                Subtask.deleted_at.is_(None),
            )
        )
        if total and total > 0:
            progress = int((completed or 0) / total * 100)
        else:
            progress = 0

        task = await db.scalar(select(Task).where(Task.id == task_id))
        if task:
            task.progress_percentage = progress
            if progress == 100 and task.status not in ("completed", "cancelled"):
                pass  # Let user explicitly mark as completed
            await db.flush()
