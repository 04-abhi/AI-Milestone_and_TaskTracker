from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task, Subtask, TaskStatus
from app.schemas.task import TaskCreate, TaskUpdate, SubtaskCreate, SubtaskUpdate


# ── Tasks ──────────────────────────────────────────────────

async def create_task(db: AsyncSession, user_id: int, data: TaskCreate) -> Task:
    task = Task(
        user_id=user_id,
        title=data.title,
        description=data.description,
        priority=data.priority,
        due_date=data.due_date,
        tags=data.tags,
    )
    db.add(task)
    await db.flush()
    await db.refresh(task)
    return task


async def get_task(db: AsyncSession, task_id: int, user_id: int) -> Optional[Task]:
    return await db.scalar(
        select(Task).where(Task.id == task_id, Task.user_id == user_id)
    )


async def get_task_with_subtasks(
    db: AsyncSession, task_id: int, user_id: int
) -> Optional[Task]:
    task = await get_task(db, task_id, user_id)
    if task:
        task._subtasks = await get_subtasks(db, task_id)
    return task


async def list_tasks(
    db: AsyncSession,
    user_id: int,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    search: Optional[str] = None,
    tag: Optional[str] = None,
    include_archived: bool = False,
    page: int = 1,
    per_page: int = 20,
) -> Tuple[List[Task], int]:
    query = select(Task).where(Task.user_id == user_id)

    if not include_archived:
        query = query.where(Task.is_archived == False)

    if status:
        query = query.where(Task.status == status)
    if priority:
        query = query.where(Task.priority == priority)
    if search:
        query = query.where(Task.title.ilike(f"%{search}%"))
    if tag:
        # tags is stored as "work,client,urgent" — search for the tag
        query = query.where(Task.tags.ilike(f"%{tag}%"))

    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0

    tasks = (
        await db.scalars(
            query.order_by(Task.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
    ).all()

    # Attach subtasks to each task
    result = []
    for task in tasks:
        subs = await get_subtasks(db, task.id)
        task.__dict__["subtasks"] = subs
        result.append(task)

    return result, total


async def update_task(db: AsyncSession, task: Task, data: TaskUpdate) -> Task:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    await db.flush()
    await db.refresh(task)
    return task


async def delete_task(db: AsyncSession, task: Task) -> None:
    await db.delete(task)
    await db.flush()


async def archive_task(db: AsyncSession, task: Task) -> Task:
    task.is_archived = True
    await db.flush()
    await db.refresh(task)
    return task


# ── Subtasks ───────────────────────────────────────────────

async def get_subtasks(db: AsyncSession, task_id: int) -> List[Subtask]:
    result = await db.scalars(
        select(Subtask)
        .where(Subtask.task_id == task_id)
        .order_by(Subtask.sort_order, Subtask.created_at)
    )
    return list(result.all())


async def create_subtask(
    db: AsyncSession, task_id: int, user_id: int, data: SubtaskCreate
) -> Subtask:
    sub = Subtask(
        task_id=task_id,
        user_id=user_id,
        title=data.title,
        sort_order=data.sort_order,
    )
    db.add(sub)
    await db.flush()
    await db.refresh(sub)
    return sub


async def get_subtask(
    db: AsyncSession, subtask_id: int, user_id: int
) -> Optional[Subtask]:
    return await db.scalar(
        select(Subtask).where(
            Subtask.id == subtask_id,
            Subtask.user_id == user_id,
        )
    )


async def update_subtask(
    db: AsyncSession, sub: Subtask, data: SubtaskUpdate
) -> Subtask:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(sub, field, value)
    await db.flush()
    await db.refresh(sub)
    return sub


async def delete_subtask(db: AsyncSession, sub: Subtask) -> None:
    await db.delete(sub)
    await db.flush()


# ── Scheduler helpers ──────────────────────────────────────

async def get_due_soon_tasks(db: AsyncSession) -> List[Task]:
    now  = datetime.now(timezone.utc)
    soon = now + timedelta(hours=24)
    tasks = (
        await db.scalars(
            select(Task).where(
                Task.due_date >= now,
                Task.due_date <= soon,
                Task.status != TaskStatus.DONE,
                Task.is_archived == False,
                Task.reminder_sent == False,
            )
        )
    ).all()
    return list(tasks)


async def mark_reminder_sent(db: AsyncSession, task: Task) -> None:
    task.reminder_sent = True
    await db.flush()


# ── Procrastination ────────────────────────────────────────

def compute_procrastination_score(task: Task) -> int:
    """
    Score 0–3:
      1 = overdue only
      2 = overdue + stale (no update in 3+ days) OR extended deadline once
      3 = all of the above / extended 2+ times
    """
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    score = 0

    if task.status in (TaskStatus.DONE,) or task.is_archived:
        return 0

    # Overdue check
    if task.due_date and task.due_date < now:
        score += 1

    # Stale check: updated_at hasn't changed in 3+ days and still not done
    stale_threshold = now - timedelta(days=3)
    if task.updated_at and task.updated_at.replace(tzinfo=timezone.utc) < stale_threshold:
        score += 1

    # Deadline extended multiple times
    if task.deadline_extended_count and task.deadline_extended_count >= 2:
        score += 1

    return min(score, 3)


async def get_procrastinated_tasks(
    db: AsyncSession, user_id: int
) -> List[Task]:
    tasks = (
        await db.scalars(
            select(Task).where(
                Task.user_id == user_id,
                Task.status != TaskStatus.DONE,
                Task.is_archived == False,
            )
        )
    ).all()

    scored = []
    for task in tasks:
        score = compute_procrastination_score(task)
        if score > 0:
            task.__dict__["procrastination_score"] = score
            subs = await get_subtasks(db, task.id)
            task.__dict__["subtasks"] = subs
            scored.append(task)

    scored.sort(key=lambda t: t.__dict__.get("procrastination_score", 0), reverse=True)
    return scored


async def reschedule_task(
    db: AsyncSession, task: Task, new_due_date
) -> Task:
    # preserve original due date on first extension
    if not task.original_due_date and task.due_date:
        task.original_due_date = task.due_date
    task.due_date = new_due_date
    task.deadline_extended_count = (task.deadline_extended_count or 0) + 1
    task.procrastination_notified = False   # reset so it can be flagged again
    await db.flush()
    await db.refresh(task)
    return task


async def reschedule_by_tag(
    db: AsyncSession, user_id: int, tag: str, new_due_date
) -> List[Task]:
    tasks = (
        await db.scalars(
            select(Task).where(
                Task.user_id == user_id,
                Task.tags.ilike(f"%{tag}%"),
                Task.status != TaskStatus.DONE,
                Task.is_archived == False,
            )
        )
    ).all()
    result = []
    for task in tasks:
        updated = await reschedule_task(db, task, new_due_date)
        updated.__dict__["subtasks"] = await get_subtasks(db, task.id)
        result.append(updated)
    return result


async def get_overdue_unnotified_tasks(db: AsyncSession) -> List[Task]:
    now = datetime.now(timezone.utc)
    tasks = (
        await db.scalars(
            select(Task).where(
                Task.due_date < now,
                Task.status != TaskStatus.DONE,
                Task.is_archived == False,
                Task.procrastination_notified == False,
            )
        )
    ).all()
    return list(tasks)


async def mark_procrastination_notified(db: AsyncSession, task: Task) -> None:
    task.procrastination_notified = True
    await db.flush()
