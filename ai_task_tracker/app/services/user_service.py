"""User service – business logic for user management."""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import get_password_hash, verify_password
from app.models.user import User
from app.schemas.user import AdminUserUpdate, UserCreate, UserUpdate


class UserService:

    @staticmethod
    async def create(db: AsyncSession, data: UserCreate) -> User:
        """Create a new user."""
        # Check email uniqueness
        existing = await db.scalar(select(User).where(User.email == data.email))
        if existing:
            raise ConflictError("Email already registered")

        existing = await db.scalar(select(User).where(User.username == data.username))
        if existing:
            raise ConflictError("Username already taken")

        user = User(
            username=data.username,
            email=data.email,
            hashed_password=get_password_hash(data.password),
            full_name=data.full_name,
            bio=data.bio,
            timezone=data.timezone,
            theme=data.theme,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: int) -> Optional[User]:
        return await db.scalar(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        return await db.scalar(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> Optional[User]:
        return await db.scalar(
            select(User).where(User.username == username, User.deleted_at.is_(None))
        )

    @staticmethod
    async def authenticate(db: AsyncSession, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = await UserService.get_by_email(db, email)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    async def update(db: AsyncSession, user: User, data: UserUpdate) -> User:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def admin_update(db: AsyncSession, user: User, data: AdminUserUpdate) -> User:
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def change_password(
        db: AsyncSession, user: User, current_password: str, new_password: str
    ) -> bool:
        if not verify_password(current_password, user.hashed_password):
            return False
        user.hashed_password = get_password_hash(new_password)
        await db.flush()
        return True

    @staticmethod
    async def soft_delete(db: AsyncSession, user: User) -> None:
        user.deleted_at = datetime.now(timezone.utc)
        user.is_active = False
        await db.flush()

    @staticmethod
    async def update_last_active(db: AsyncSession, user_id: int) -> None:
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(last_active_at=datetime.now(timezone.utc))
        )

    @staticmethod
    async def update_task_stats(db: AsyncSession, user_id: int) -> None:
        """Recalculate and update task stats for a user."""
        from app.models.task import Task, TaskStatus
        total = await db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user_id, Task.deleted_at.is_(None)
            )
        )
        completed = await db.scalar(
            select(func.count(Task.id)).where(
                Task.user_id == user_id,
                Task.status == TaskStatus.COMPLETED,
                Task.deleted_at.is_(None),
            )
        )
        await db.execute(
            update(User)
            .where(User.id == user_id)
            .values(total_tasks=total or 0, completed_tasks=completed or 0)
        )

    @staticmethod
    async def list_all(
        db: AsyncSession, skip: int = 0, limit: int = 50
    ) -> tuple[List[User], int]:
        """List all users (admin)."""
        total = await db.scalar(
            select(func.count(User.id)).where(User.deleted_at.is_(None))
        )
        users = (
            await db.scalars(
                select(User)
                .where(User.deleted_at.is_(None))
                .order_by(User.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
        ).all()
        return list(users), total or 0
