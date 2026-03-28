"""Task service – business logic for task management."""
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.models.task import Task, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate


class TaskService:

    @staticmethod
    async def create(db: AsyncSession, user_id: int, data: TaskCreate) -> Task:
        task = Task(
            user_id=user_id,
            title=data.title,
            description=data.description,
            priority=data.priority,
            category=data.category,
            tags=data.tags,
            due_date=data.due_date,
            estimated_hours=data.estimated_hours,
            is_pinned=data.is_pinned,
            is_recurring=data.is_recurring,
            recurrence_pattern=data.recurrence_pattern,
            milestone_id=data.milestone_id,
        )
        db.add(task)
        await db.flush()
        await db.refresh(task, ["subtasks"])
        # Update user stats
        from app.services.user_service import UserService
        await UserService.update_task_stats(db, user_id)
        return task

    @staticmethod
    async def get_by_id(db: AsyncSession, task_id: int, user_id: int) -> Optional[Task]:
        return await db.scalar(
            select(Task)
            .options(selectinload(Task.subtasks))
            .where(Task.id == task_id, Task.user_id == user_id, Task.deleted_at.is_(None))
        )

    @staticmethod
    async def get_or_raise(db: AsyncSession, task_id: int, user_id: int) -> Task:
        task = await TaskService.get_by_id(db, task_id, user_id)
        if not task:
            raise NotFoundError("Task")
        return task

    @staticmethod
    async def list_tasks(
        db: AsyncSession,
        user_id: int,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        milestone_id: Optional[int] = None,
        search: Optional[str] = None,
        is_pinned: Optional[bool] = None,
        due_date_from: Optional[datetime] = None,
        due_date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> Tuple[List[Task], int]:
        query = select(Task).where(Task.user_id == user_id, Task.deleted_at.is_(None))

        if status:
            query = query.where(Task.status == status)
        if priority:
            query = query.where(Task.priority == priority)
        if category:
            query = query.where(Task.category == category)
        if milestone_id is not None:
            query = query.where(Task.milestone_id == milestone_id)
        if is_pinned is not None:
            query = query.where(Task.is_pinned == is_pinned)
        if search:
            query = query.where(
                or_(Task.title.ilike(f"%{search}%"), Task.description.ilike(f"%{search}%"))
            )
        if due_date_from:
            query = query.where(Task.due_date >= due_date_from)
        if due_date_to:
            query = query.where(Task.due_date <= due_date_to)

        count_query = select(func.count()).select_from(query.subquery())
        total = await db.scalar(count_query) or 0

        sort_col = getattr(Task, sort_by, Task.created_at)
        if sort_order == "asc":
            query = query.order_by(Task.is_pinned.desc(), sort_col.asc())
        else:
            query = query.order_by(Task.is_pinned.desc(), sort_col.desc())

        tasks = (await db.scalars(query.offset(skip).limit(limit))).all()
        return list(tasks), total

    @staticmethod
    async def update(db: AsyncSession, task: Task, data: TaskUpdate) -> Task:
        update_data = data.model_dump(exclude_unset=True)

        # Handle status transitions
        if "status" in update_data:
            new_status = update_data["status"]
            if new_status == TaskStatus.IN_PROGRESS and not task.started_at:
                task.started_at = datetime.now(timezone.utc)
            elif new_status == TaskStatus.COMPLETED and not task.completed_at:
                task.completed_at = datetime.now(timezone.utc)
                task.progress_percentage = 100
            elif new_status in (TaskStatus.TODO, TaskStatus.ON_HOLD):
                task.completed_at = None

        for field, value in update_data.items():
            setattr(task, field, value)

        await db.flush()
        await db.refresh(task, ["subtasks"])

        from app.services.user_service import UserService
        await UserService.update_task_stats(db, task.user_id)

        # Update milestone progress if linked
        if task.milestone_id:
            from app.services.milestone_service import MilestoneService
            await MilestoneService.recalculate_progress(db, task.milestone_id)

        return task

    @staticmethod
    async def delete(db: AsyncSession, task: Task) -> None:
        task.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        from app.services.user_service import UserService
        await UserService.update_task_stats(db, task.user_id)

    @staticmethod
    async def bulk_delete(db: AsyncSession, user_id: int, task_ids: List[int]) -> int:
        tasks = (
            await db.scalars(
                select(Task).where(
                    Task.id.in_(task_ids),
                    Task.user_id == user_id,
                    Task.deleted_at.is_(None),
                )
            )
        ).all()
        now = datetime.now(timezone.utc)
        for task in tasks:
            task.deleted_at = now
        await db.flush()
        from app.services.user_service import UserService
        await UserService.update_task_stats(db, user_id)
        return len(tasks)

    @staticmethod
    async def get_overdue_tasks(db: AsyncSession, user_id: int) -> List[Task]:
        now = datetime.now(timezone.utc)
        tasks = (
            await db.scalars(
                select(Task).where(
                    Task.user_id == user_id,
                    Task.due_date < now,
                    Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
                    Task.deleted_at.is_(None),
                )
            )
        ).all()
        return list(tasks)

    @staticmethod
    async def get_due_soon_tasks(db: AsyncSession, user_id: int, hours: int = 72) -> List[Task]:
        from datetime import timedelta
        now = datetime.now(timezone.utc)
        soon = now + timedelta(hours=hours)
        tasks = (
            await db.scalars(
                select(Task).where(
                    Task.user_id == user_id,
                    Task.due_date >= now,
                    Task.due_date <= soon,
                    Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
                    Task.deleted_at.is_(None),
                )
            )
        ).all()
        return list(tasks)

    @staticmethod
    async def admin_list_all(
        db: AsyncSession, skip: int = 0, limit: int = 50
    ) -> Tuple[List[Task], int]:
        total = await db.scalar(
            select(func.count(Task.id)).where(Task.deleted_at.is_(None))
        )
        tasks = (
            await db.scalars(
                select(Task)
                .where(Task.deleted_at.is_(None))
                .order_by(Task.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
        ).all()
        return list(tasks), total or 0
