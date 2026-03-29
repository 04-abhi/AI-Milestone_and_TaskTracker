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
    scheduler.start()
    logger.info("Scheduler started — reminders run every 15 minutes")


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
