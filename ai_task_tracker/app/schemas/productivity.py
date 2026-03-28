"""Productivity Pydantic schemas."""
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class ProductivityLogResponse(BaseModel):
    id: int
    user_id: int
    log_date: date
    tasks_created: int
    tasks_completed: int
    tasks_overdue: int
    tasks_cancelled: int
    subtasks_completed: int
    total_estimated_hours: float
    total_actual_hours: float
    active_minutes: int
    productivity_score: float
    completion_rate: float
    on_time_rate: float
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductivitySummary(BaseModel):
    period_days: int
    total_tasks_created: int
    total_tasks_completed: int
    total_tasks_overdue: int
    average_productivity_score: float
    average_completion_rate: float
    average_on_time_rate: float
    best_day: Optional[date]
    worst_day: Optional[date]
    current_streak: int
    longest_streak: int
    total_hours_logged: float
    category_breakdown: Dict[str, int]
    daily_scores: List[Dict[str, Any]]


class DashboardStats(BaseModel):
    total_tasks: int
    tasks_today: int
    tasks_due_soon: int  # next 3 days
    tasks_overdue: int
    completed_today: int
    active_milestones: int
    completion_rate_7d: float
    productivity_score_today: float
    streak_days: int
    unread_notifications: int
    pending_suggestions: int
