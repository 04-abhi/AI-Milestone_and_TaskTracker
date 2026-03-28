"""AI Suggestion model."""
import enum
from typing import Optional

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class SuggestionType(str, enum.Enum):
    PRIORITIZATION = "prioritization"
    TIME_MANAGEMENT = "time_management"
    WORKLOAD_BALANCE = "workload_balance"
    OVERDUE_ALERT = "overdue_alert"
    BREAK_REMINDER = "break_reminder"
    PRODUCTIVITY_BOOST = "productivity_boost"
    STREAK_MOTIVATION = "streak_motivation"
    TASK_BREAKDOWN = "task_breakdown"
    DEADLINE_WARNING = "deadline_warning"
    FOCUS_MODE = "focus_mode"


class SuggestionStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    EXPIRED = "expired"


class AISuggestion(Base, TimestampMixin):
    __tablename__ = "ai_suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    suggestion_type: Mapped[SuggestionType] = mapped_column(Enum(SuggestionType), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    action_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON string

    status: Mapped[SuggestionStatus] = mapped_column(Enum(SuggestionStatus), default=SuggestionStatus.PENDING, nullable=False)
    confidence_score: Mapped[float] = mapped_column(default=1.0, nullable=False)  # 0-1
    priority_score: Mapped[int] = mapped_column(Integer, default=50, nullable=False)  # 0-100

    # Context that triggered this suggestion
    trigger_context: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    related_task_ids: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON array

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="ai_suggestions")

    def __repr__(self) -> str:
        return f"<AISuggestion id={self.id} type={self.suggestion_type} status={self.status}>"
