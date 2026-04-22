"""
Background Scheduler
Runs every 15 minutes:
  - Finds tasks due within 24 hours
  - Sends push notification to task owner
  - Marks reminder_sent = True to avoid repeat spam
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from loguru import logger

scheduler = AsyncIOScheduler(timezone="UTC")


def start_scheduler():
    scheduler.add_job(
        _send_reminders,
        IntervalTrigger(minutes=15),
        id="due_reminders",
        replace_existing=True,
    )
    scheduler.add_job(
        _send_procrastination_alerts,
        IntervalTrigger(hours=6),
        id="procrastination_alerts",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — reminders every 15 min, procrastination checks every 6 hours")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)


async def _send_reminders():
    logger.info("Scheduler: checking for due tasks…")
    try:
        from app.db.session import AsyncSessionLocal
        from app.services.task_service import get_due_soon_tasks, mark_reminder_sent
        from app.services.push_service import send_push_to_user
        from datetime import datetime, timezone

        async with AsyncSessionLocal() as db:
            tasks = await get_due_soon_tasks(db)
            for task in tasks:
                now = datetime.now(timezone.utc)
                diff = task.due_date - now
                hours = int(diff.total_seconds() / 3600)
                time_str = f"{hours}h" if hours > 0 else "less than 1h"

                await send_push_to_user(
                    db,
                    user_id=task.user_id,
                    title=f"⏰ Task due in {time_str}",
                    body=task.title,
                    url="/",
                )
                await mark_reminder_sent(db, task)
            await db.commit()
            if tasks:
                logger.info(f"Scheduler: sent {len(tasks)} reminder(s)")
    except Exception as e:
        logger.error(f"Scheduler error: {e}")


async def _send_procrastination_alerts():
    logger.info("Scheduler: checking for procrastinated tasks…")
    try:
        from app.db.session import AsyncSessionLocal
        from app.services.task_service import (
            get_overdue_unnotified_tasks, mark_procrastination_notified
        )
        from app.services.push_service import send_push_to_user

        async with AsyncSessionLocal() as db:
            tasks = await get_overdue_unnotified_tasks(db)

            # Group by user
            by_user: dict = {}
            for task in tasks:
                by_user.setdefault(task.user_id, []).append(task)

            for user_id, user_tasks in by_user.items():
                count = len(user_tasks)
                names = ", ".join(t.title for t in user_tasks[:2])
                body = f"{names}{' and more…' if count > 2 else ''}"

                await send_push_to_user(
                    db,
                    user_id=user_id,
                    title=f"⏰ {count} task{'s' if count > 1 else ''} need your attention",
                    body=body,
                    url="/#procrastination",
                )
                for task in user_tasks:
                    await mark_procrastination_notified(db, task)

            await db.commit()
            if tasks:
                logger.info(f"Scheduler: sent procrastination alerts for {len(tasks)} task(s)")
    except Exception as e:
        logger.error(f"Procrastination scheduler error: {e}")
