"""Productivity log model for analytics."""
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class ProductivityLog(Base, TimestampMixin):
    __tablename__ = "productivity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    log_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # Task metrics
    tasks_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tasks_overdue: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tasks_cancelled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    subtasks_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Time metrics
    total_estimated_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_actual_hours: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    active_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Score (0-100)
    productivity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    completion_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0-1
    on_time_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)  # 0-1

    # Category breakdown (stored as JSON string)
    category_breakdown: Mapped[Optional[str]] = mapped_column(nullable=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="productivity_logs")

    def __repr__(self) -> str:
        return f"<ProductivityLog user={self.user_id} date={self.log_date} score={self.productivity_score}>"
