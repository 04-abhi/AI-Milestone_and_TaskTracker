from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.models.task import Task, TaskStatus, TaskPriority
from app.schemas.user import UserRegister, UserUpdate


async def create_user(db: AsyncSession, data: UserRegister) -> User:
    existing = await db.scalar(select(User).where(User.email == data.email))
    if existing:
        raise ValueError("Email already registered")
    existing = await db.scalar(select(User).where(User.username == data.username))
    if existing:
        raise ValueError("Username already taken")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)

    # Seed 3 example tasks so the dashboard is never empty for new users
    await _seed_example_tasks(db, user.id)

    return user


async def _seed_example_tasks(db: AsyncSession, user_id: int) -> None:
    now = datetime.now(timezone.utc)
    examples = [
        Task(
            user_id=user_id,
            title="👋 Welcome to AI Task Tracker!",
            description=(
                "This is a sample task. Click the ✏️ button to edit it, "
                "or the ✓ circle to mark it done. Press N anywhere to create a new task."
            ),
            status=TaskStatus.TODO,
            priority=TaskPriority.LOW,
            due_date=now + timedelta(days=1),
            tags="welcome,getting-started",
        ),
        Task(
            user_id=user_id,
            title="📅 Try the Calendar view",
            description=(
                "Click 'Calendar' in the sidebar to see your tasks laid out by week. "
                "Tasks with due dates appear on their scheduled day."
            ),
            status=TaskStatus.TODO,
            priority=TaskPriority.MEDIUM,
            due_date=now + timedelta(days=3),
            tags="tips",
        ),
        Task(
            user_id=user_id,
            title="🔔 Enable push notifications",
            description=(
                "Go to Settings → Push Notifications and click 'Enable Notifications'. "
                "You'll get reminders on your phone when tasks are due soon."
            ),
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            due_date=now + timedelta(days=7),
            tags="tips,notifications",
        ),
    ]
    for task in examples:
        db.add(task)
    await db.flush()


async def authenticate(db: AsyncSession, email: str, password: str) -> Optional[User]:
    user = await db.scalar(select(User).where(User.email == email))
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


async def get_user(db: AsyncSession, user_id: int) -> Optional[User]:
    return await db.scalar(select(User).where(User.id == user_id))


async def update_user(db: AsyncSession, user: User, data: UserUpdate) -> User:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    await db.flush()
    await db.refresh(user)
    return user


async def change_password(
    db: AsyncSession, user: User, current: str, new: str
) -> bool:
    if not verify_password(current, user.hashed_password):
        return False
    user.hashed_password = hash_password(new)
    await db.flush()
    return True


async def delete_user(db: AsyncSession, user: User) -> None:
    await db.delete(user)
    await db.flush()
