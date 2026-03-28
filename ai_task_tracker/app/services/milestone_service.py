"""Milestone service."""
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.milestone import Milestone, MilestoneStatus
from app.models.task import Task, TaskStatus
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate


class MilestoneService:

    @staticmethod
    async def create(db: AsyncSession, user_id: int, data: MilestoneCreate) -> Milestone:
        milestone = Milestone(
            user_id=user_id,
            title=data.title,
            description=data.description,
            color=data.color,
            icon=data.icon,
            start_date=data.start_date,
            due_date=data.due_date,
        )
        db.add(milestone)
        await db.flush()
        await db.refresh(milestone)
        return milestone

    @staticmethod
    async def get_by_id(db: AsyncSession, milestone_id: int, user_id: int) -> Optional[Milestone]:
        return await db.scalar(
            select(Milestone).where(
                Milestone.id == milestone_id,
                Milestone.user_id == user_id,
                Milestone.deleted_at.is_(None),
            )
        )

    @staticmethod
    async def get_or_raise(db: AsyncSession, milestone_id: int, user_id: int) -> Milestone:
        milestone = await MilestoneService.get_by_id(db, milestone_id, user_id)
        if not milestone:
            raise NotFoundError("Milestone")
        return milestone

    @staticmethod
    async def list_milestones(
        db: AsyncSession,
        user_id: int,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Milestone], int]:
        query = select(Milestone).where(
            Milestone.user_id == user_id, Milestone.deleted_at.is_(None)
        )
        if status:
            query = query.where(Milestone.status == status)

        total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
        milestones = (
            await db.scalars(query.order_by(Milestone.due_date.asc().nulls_last()).offset(skip).limit(limit))
        ).all()
        return list(milestones), total

    @staticmethod
    async def update(db: AsyncSession, milestone: Milestone, data: MilestoneUpdate) -> Milestone:
        update_data = data.model_dump(exclude_unset=True)

        if "status" in update_data:
            if update_data["status"] == MilestoneStatus.COMPLETED and not milestone.completed_at:
                milestone.completed_at = datetime.now(timezone.utc)
            elif update_data["status"] != MilestoneStatus.COMPLETED:
                milestone.completed_at = None

        for field, value in update_data.items():
            setattr(milestone, field, value)

        await db.flush()
        await db.refresh(milestone)
        return milestone

    @staticmethod
    async def delete(db: AsyncSession, milestone: Milestone) -> None:
        milestone.deleted_at = datetime.now(timezone.utc)
        await db.flush()

    @staticmethod
    async def recalculate_progress(db: AsyncSession, milestone_id: int) -> None:
        """Recalculate milestone progress from its tasks."""
        total = await db.scalar(
            select(func.count(Task.id)).where(
                Task.milestone_id == milestone_id,
                Task.deleted_at.is_(None),
            )
        )
        completed = await db.scalar(
            select(func.count(Task.id)).where(
                Task.milestone_id == milestone_id,
                Task.status == TaskStatus.COMPLETED,
                Task.deleted_at.is_(None),
            )
        )
        milestone = await db.scalar(select(Milestone).where(Milestone.id == milestone_id))
        if milestone:
            milestone.total_tasks = total or 0
            milestone.completed_tasks = completed or 0
            milestone.progress_percentage = int((completed or 0) / (total or 1) * 100)

            # Auto-update status
            if milestone.progress_percentage == 100:
                milestone.status = MilestoneStatus.COMPLETED
                if not milestone.completed_at:
                    milestone.completed_at = datetime.now(timezone.utc)
            elif milestone.due_date and milestone.due_date < datetime.now(timezone.utc):
                milestone.status = MilestoneStatus.OVERDUE
            elif milestone.progress_percentage > 0:
                milestone.status = MilestoneStatus.IN_PROGRESS

            await db.flush()
