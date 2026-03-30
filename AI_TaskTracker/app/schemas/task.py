from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from app.models.task import TaskPriority, TaskStatus


# ── Subtask schemas ────────────────────────────────────────

class SubtaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    sort_order: int = 0


class SubtaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    is_done: Optional[bool] = None
    sort_order: Optional[int] = None


class SubtaskOut(BaseModel):
    id: int
    task_id: int
    title: str
    is_done: bool
    sort_order: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Task schemas ───────────────────────────────────────────

class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    tags: Optional[str] = None   # comma-separated e.g. "work,client"


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    due_date: Optional[datetime] = None
    tags: Optional[str] = None
    is_archived: Optional[bool] = None


class TaskOut(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    due_date: Optional[datetime]
    tags: Optional[str]
    is_archived: bool
    reminder_sent: bool
    created_at: datetime
    updated_at: datetime
    subtasks: List[SubtaskOut] = []

    model_config = {"from_attributes": True}


class TaskListOut(BaseModel):
    items: List[TaskOut]
    total: int
    page: int
    per_page: int
    total_pages: int
