"""Productivity analytics service."""
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.productivity import ProductivityLog
from app.models.task import Task, TaskCategory, TaskStatus
from app.models.subtask import Subtask, SubtaskStatus
from app.models.user import User
from app.schemas.productivity import DashboardStats, ProductivitySummary


class ProductivityService:

    @staticmethod
    async def record_daily_log(db: AsyncSession, user_id: int, log_date: Optional[date] = None) -> ProductivityLog:
        """Create or update a daily productivity snapshot for the user."""
        if log_date is None:
            log_date = datetime.now(timezone.utc).date()

        # Check for existing log
        existing = await db.scalar(
            select(ProductivityLog).where(
                ProductivityLog.user_id == user_id,
                ProductivityLog.log_date == log_date,
            )
        )

        day_start = datetime.combine(log_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        day_end = day_start + timedelta(days=1)

        # Gather metrics
        tasks_created = await db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.created_at >= day_start,
                Task.created_at < day_end,
                Task.deleted_at.is_(None),
            )
        ) or 0

        tasks_completed = await db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= day_start,
                Task.completed_at < day_end,
                Task.deleted_at.is_(None),
            )
        ) or 0

        tasks_overdue = await db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.due_date < day_end,
                Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
                Task.deleted_at.is_(None),
            )
        ) or 0

        tasks_cancelled = await db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.status == TaskStatus.CANCELLED,
                Task.updated_at >= day_start,
                Task.updated_at < day_end,
                Task.deleted_at.is_(None),
            )
        ) or 0

        subtasks_completed = await db.scalar(
            select(func.count(Subtask.id)).where(
                Subtask.task_id.in_(
                    select(Task.id).where(Task.user_id == user_id)
                ),
                Subtask.status == SubtaskStatus.COMPLETED,
                Subtask.completed_at >= day_start,
                Subtask.completed_at < day_end,
                Subtask.deleted_at.is_(None),
            )
        ) or 0

        # Completion rate
        completion_rate = tasks_completed / max(tasks_created, 1)
        on_time_rate = (tasks_completed / max(tasks_completed + tasks_overdue, 1))

        # Productivity score (0-100)
        # Weighted formula: 40% completion_rate + 30% on_time + 20% tasks_done + 10% bonus
        score = min(
            100,
            (completion_rate * 40)
            + (on_time_rate * 30)
            + (min(tasks_completed / 5, 1.0) * 20)
            + (min(subtasks_completed / 10, 1.0) * 10),
        )

        # Category breakdown
        category_rows = (
            await db.execute(
                select(Task.category, func.count(Task.id)).where(
                    Task.user_id == user_id,
                    Task.status == TaskStatus.COMPLETED,
                    Task.completed_at >= day_start,
                    Task.completed_at < day_end,
                    Task.deleted_at.is_(None),
                ).group_by(Task.category)
            )
        ).all()
        import json
        category_breakdown = json.dumps({row[0].value: row[1] for row in category_rows})

        if existing:
            existing.tasks_created = tasks_created
            existing.tasks_completed = tasks_completed
            existing.tasks_overdue = tasks_overdue
            existing.tasks_cancelled = tasks_cancelled
            existing.subtasks_completed = subtasks_completed
            existing.completion_rate = round(completion_rate, 4)
            existing.on_time_rate = round(on_time_rate, 4)
            existing.productivity_score = round(score, 2)
            existing.category_breakdown = category_breakdown
            await db.flush()
            return existing

        log = ProductivityLog(
            user_id=user_id,
            log_date=log_date,
            tasks_created=tasks_created,
            tasks_completed=tasks_completed,
            tasks_overdue=tasks_overdue,
            tasks_cancelled=tasks_cancelled,
            subtasks_completed=subtasks_completed,
            completion_rate=round(completion_rate, 4),
            on_time_rate=round(on_time_rate, 4),
            productivity_score=round(score, 2),
            category_breakdown=category_breakdown,
        )
        db.add(log)
        await db.flush()
        await db.refresh(log)
        return log

    @staticmethod
    async def get_summary(db: AsyncSession, user_id: int, days: int = 30) -> ProductivitySummary:
        since = (datetime.now(timezone.utc) - timedelta(days=days)).date()

        logs = (
            await db.scalars(
                select(ProductivityLog).where(
                    ProductivityLog.user_id == user_id,
                    ProductivityLog.log_date >= since,
                ).order_by(ProductivityLog.log_date.asc())
            )
        ).all()

        if not logs:
            return ProductivitySummary(
                period_days=days,
                total_tasks_created=0,
                total_tasks_completed=0,
                total_tasks_overdue=0,
                average_productivity_score=0.0,
                average_completion_rate=0.0,
                average_on_time_rate=0.0,
                best_day=None,
                worst_day=None,
                current_streak=0,
                longest_streak=0,
                total_hours_logged=0.0,
                category_breakdown={},
                daily_scores=[],
            )

        total_created = sum(l.tasks_created for l in logs)
        total_completed = sum(l.tasks_completed for l in logs)
        total_overdue = sum(l.tasks_overdue for l in logs)
        avg_score = sum(l.productivity_score for l in logs) / len(logs)
        avg_completion = sum(l.completion_rate for l in logs) / len(logs)
        avg_on_time = sum(l.on_time_rate for l in logs) / len(logs)
        total_hours = sum(l.total_actual_hours for l in logs)

        best = max(logs, key=lambda l: l.productivity_score)
        worst = min(logs, key=lambda l: l.productivity_score)

        # Streak calculation
        user = await db.scalar(select(User).where(User.id == user_id))
        streak = user.streak_days if user else 0

        # Category breakdown aggregate
        import json
        category_agg: Dict[str, int] = {}
        for log in logs:
            if log.category_breakdown:
                try:
                    cb = json.loads(log.category_breakdown)
                    for cat, count in cb.items():
                        category_agg[cat] = category_agg.get(cat, 0) + count
                except Exception:
                    pass

        daily_scores = [
            {"date": str(l.log_date), "score": l.productivity_score, "completed": l.tasks_completed}
            for l in logs
        ]

        return ProductivitySummary(
            period_days=days,
            total_tasks_created=total_created,
            total_tasks_completed=total_completed,
            total_tasks_overdue=total_overdue,
            average_productivity_score=round(avg_score, 2),
            average_completion_rate=round(avg_completion, 4),
            average_on_time_rate=round(avg_on_time, 4),
            best_day=best.log_date,
            worst_day=worst.log_date,
            current_streak=streak,
            longest_streak=streak,  # simplified – can be extended
            total_hours_logged=round(total_hours, 2),
            category_breakdown=category_agg,
            daily_scores=daily_scores,
        )

    @staticmethod
    async def get_dashboard_stats(db: AsyncSession, user_id: int) -> DashboardStats:
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        three_days = now + timedelta(days=3)

        total_tasks = await db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user_id, Task.deleted_at.is_(None)
            )
        ) or 0

        tasks_today = await db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.due_date >= today_start,
                Task.due_date < today_start + timedelta(days=1),
                Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
                Task.deleted_at.is_(None),
            )
        ) or 0

        tasks_due_soon = await db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.due_date >= now,
                Task.due_date <= three_days,
                Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
                Task.deleted_at.is_(None),
            )
        ) or 0

        tasks_overdue = await db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.due_date < now,
                Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
                Task.deleted_at.is_(None),
            )
        ) or 0

        completed_today = await db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.completed_at >= today_start,
                Task.deleted_at.is_(None),
            )
        ) or 0

        from app.models.milestone import Milestone, MilestoneStatus
        active_milestones = await db.scalar(
            select(func.count(Milestone.id)).where(
                Milestone.user_id == user_id,
                Milestone.status.in_([MilestoneStatus.PLANNED, MilestoneStatus.IN_PROGRESS]),
                Milestone.deleted_at.is_(None),
            )
        ) or 0

        # 7-day completion rate
        seven_days_ago = (now - timedelta(days=7)).date()
        logs_7d = (
            await db.scalars(
                select(ProductivityLog).where(
                    ProductivityLog.user_id == user_id,
                    ProductivityLog.log_date >= seven_days_ago,
                )
            )
        ).all()
        completion_rate_7d = sum(l.completion_rate for l in logs_7d) / len(logs_7d) if logs_7d else 0.0

        # Today's productivity score
        today_log = await db.scalar(
            select(ProductivityLog).where(
                ProductivityLog.user_id == user_id,
                ProductivityLog.log_date == now.date(),
            )
        )
        productivity_score_today = today_log.productivity_score if today_log else 0.0

        user = await db.scalar(select(User).where(User.id == user_id))
        streak_days = user.streak_days if user else 0

        from app.services.notification_service import NotificationService
        unread_notifications = await NotificationService.get_unread_count(db, user_id)

        from app.models.ai_suggestion import AISuggestion, SuggestionStatus
        pending_suggestions = await db.scalar(
            select(func.count(AISuggestion.id)).where(
                AISuggestion.user_id == user_id,
                AISuggestion.status == SuggestionStatus.PENDING,
                AISuggestion.is_read == False,  # noqa: E712
            )
        ) or 0

        return DashboardStats(
            total_tasks=total_tasks,
            tasks_today=tasks_today,
            tasks_due_soon=tasks_due_soon,
            tasks_overdue=tasks_overdue,
            completed_today=completed_today,
            active_milestones=active_milestones,
            completion_rate_7d=round(completion_rate_7d, 4),
            productivity_score_today=round(productivity_score_today, 2),
            streak_days=streak_days,
            unread_notifications=unread_notifications,
            pending_suggestions=pending_suggestions,
        )
