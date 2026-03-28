"""
Background scheduler using APScheduler.

Jobs:
  - Daily productivity log snapshot (00:05 UTC)
  - AI suggestion generation (every 6 hours)
  - Overdue task notifications (hourly)
  - Session cleanup (daily)
  - Streak update (00:01 UTC)
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

scheduler = AsyncIOScheduler(timezone="UTC")


def start_scheduler():
    """Register all background jobs and start the scheduler."""

    scheduler.add_job(
        _job_record_daily_logs,
        CronTrigger(hour=0, minute=5),
        id="daily_productivity_log",
        replace_existing=True,
        name="Record daily productivity logs",
    )

    scheduler.add_job(
        _job_generate_ai_suggestions,
        IntervalTrigger(hours=6),
        id="ai_suggestions",
        replace_existing=True,
        name="Generate AI suggestions for all users",
    )

    scheduler.add_job(
        _job_overdue_notifications,
        IntervalTrigger(hours=1),
        id="overdue_notifications",
        replace_existing=True,
        name="Send overdue task notifications",
    )

    scheduler.add_job(
        _job_update_streaks,
        CronTrigger(hour=0, minute=1),
        id="update_streaks",
        replace_existing=True,
        name="Update user streaks",
    )

    scheduler.add_job(
        _job_cleanup_sessions,
        CronTrigger(hour=3, minute=0),
        id="cleanup_sessions",
        replace_existing=True,
        name="Clean up expired sessions",
    )

    scheduler.add_job(
        _job_update_milestone_statuses,
        IntervalTrigger(hours=2),
        id="milestone_status_update",
        replace_existing=True,
        name="Update overdue milestone statuses",
    )

    scheduler.start()
    logger.info("Background scheduler started with {} jobs", len(scheduler.get_jobs()))


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")


# ── Job implementations ────────────────────────────────────────────────────────

async def _job_record_daily_logs():
    """Snapshot productivity for every active user."""
    logger.info("Scheduler: recording daily productivity logs")
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.user import User
        from app.services.productivity_service import ProductivityService
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            users = (
                await db.scalars(
                    select(User).where(User.is_active == True, User.deleted_at.is_(None))  # noqa: E712
                )
            ).all()
            for user in users:
                try:
                    await ProductivityService.record_daily_log(db, user.id)
                except Exception as e:
                    logger.error(f"Failed to record log for user {user.id}: {e}")
            await db.commit()
        logger.info(f"Scheduler: recorded logs for {len(users)} users")
    except Exception as e:
        logger.error(f"Scheduler: daily log job failed – {e}")


async def _job_generate_ai_suggestions():
    """Generate AI suggestions for all active users."""
    logger.info("Scheduler: generating AI suggestions")
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.user import User
        from app.services.ai_engine import AISuggestionService
        from sqlalchemy import select

        async with AsyncSessionLocal() as db:
            users = (
                await db.scalars(
                    select(User).where(User.is_active == True, User.deleted_at.is_(None))  # noqa: E712
                )
            ).all()
            total = 0
            for user in users:
                try:
                    suggestions = await AISuggestionService.generate_for_user(db, user.id)
                    total += len(suggestions)
                except Exception as e:
                    logger.error(f"Failed AI suggestions for user {user.id}: {e}")
            await db.commit()
        logger.info(f"Scheduler: created {total} suggestions across {len(users)} users")
    except Exception as e:
        logger.error(f"Scheduler: AI suggestion job failed – {e}")


async def _job_overdue_notifications():
    """Create notifications for newly overdue tasks."""
    logger.info("Scheduler: checking overdue tasks")
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.task import Task, TaskStatus
        from app.models.notification import NotificationType, NotificationPriority
        from app.services.notification_service import NotificationService
        from sqlalchemy import select
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            overdue_tasks = (
                await db.scalars(
                    select(Task).where(
                        Task.due_date < now,
                        Task.status.not_in([TaskStatus.COMPLETED, TaskStatus.CANCELLED]),
                        Task.deleted_at.is_(None),
                    )
                )
            ).all()

            for task in overdue_tasks:
                await NotificationService.create_notification(
                    db,
                    user_id=task.user_id,
                    title=f"Task Overdue: {task.title[:50]}",
                    message=f'Your task "{task.title}" was due and has not been completed.',
                    notification_type=NotificationType.TASK_OVERDUE,
                    priority=NotificationPriority.HIGH,
                    related_entity_type="task",
                    related_entity_id=task.id,
                )
            await db.commit()
        logger.info(f"Scheduler: sent {len(overdue_tasks)} overdue notifications")
    except Exception as e:
        logger.error(f"Scheduler: overdue notification job failed – {e}")


async def _job_update_streaks():
    """Recalculate streak_days for all users based on productivity logs."""
    logger.info("Scheduler: updating user streaks")
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.user import User
        from app.models.productivity import ProductivityLog
        from app.utils.streak import calculate_streak
        from sqlalchemy import select, update

        async with AsyncSessionLocal() as db:
            users = (
                await db.scalars(
                    select(User).where(User.is_active == True, User.deleted_at.is_(None))  # noqa: E712
                )
            ).all()
            for user in users:
                logs = (
                    await db.scalars(
                        select(ProductivityLog.log_date).where(
                            ProductivityLog.user_id == user.id,
                            ProductivityLog.tasks_completed > 0,
                        )
                    )
                ).all()
                streak = calculate_streak(list(logs))
                user.streak_days = streak
            await db.commit()
        logger.info(f"Scheduler: updated streaks for {len(users)} users")
    except Exception as e:
        logger.error(f"Scheduler: streak update job failed – {e}")


async def _job_cleanup_sessions():
    """Remove expired user sessions from the database."""
    logger.info("Scheduler: cleaning up expired sessions")
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.user import UserSession
        from sqlalchemy import delete
        from datetime import datetime, timezone

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                delete(UserSession).where(
                    UserSession.expires_at < datetime.now(timezone.utc)
                )
            )
            await db.commit()
        logger.info(f"Scheduler: deleted {result.rowcount} expired sessions")
    except Exception as e:
        logger.error(f"Scheduler: session cleanup job failed – {e}")


async def _job_update_milestone_statuses():
    """Mark milestones as OVERDUE when their due_date has passed."""
    logger.info("Scheduler: updating overdue milestone statuses")
    try:
        from app.db.session import AsyncSessionLocal
        from app.models.milestone import Milestone, MilestoneStatus
        from sqlalchemy import select
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            milestones = (
                await db.scalars(
                    select(Milestone).where(
                        Milestone.due_date < now,
                        Milestone.status.not_in(
                            [MilestoneStatus.COMPLETED, MilestoneStatus.CANCELLED, MilestoneStatus.OVERDUE]
                        ),
                        Milestone.deleted_at.is_(None),
                    )
                )
            ).all()
            for m in milestones:
                m.status = MilestoneStatus.OVERDUE
            await db.commit()
        logger.info(f"Scheduler: marked {len(milestones)} milestones as overdue")
    except Exception as e:
        logger.error(f"Scheduler: milestone status job failed – {e}")
