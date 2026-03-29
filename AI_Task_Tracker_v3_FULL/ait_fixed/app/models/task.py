import enum
from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class TaskStatus(str, enum.Enum):
    TODO        = "todo"
    IN_PROGRESS = "in_progress"
    DONE        = "done"


class TaskPriority(str, enum.Enum):
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"
    URGENT = "urgent"


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus), default=TaskStatus.TODO, nullable=False
    )
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority), default=TaskPriority.MEDIUM, nullable=False
    )

    due_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Tags stored as comma-separated string e.g. "work,urgent,client"
    tags: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Soft delete — archived tasks are hidden but kept
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)

    # Push reminder tracking
    reminder_sent: Mapped[bool] = mapped_column(Boolean, default=False)

    def __repr__(self):
        return f"<Task {self.id}: {self.title}>"

    @property
    def tags_list(self):
        if not self.tags:
            return []
        return [t.strip() for t in self.tags.split(",") if t.strip()]


class Subtask(Base, TimestampMixin):
    __tablename__ = "subtasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    is_done: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    def __repr__(self):
        return f"<Subtask {self.id}: {self.title}>"
