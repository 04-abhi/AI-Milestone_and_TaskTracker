"""Task Pydantic schemas."""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.task import TaskCategory, TaskPriority, TaskStatus
from app.schemas.subtask import SubtaskResponse


class TaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    priority: TaskPriority = TaskPriority.MEDIUM
    category: TaskCategory = TaskCategory.OTHER
    tags: Optional[str] = Field(None, max_length=500)
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = Field(None, ge=0, le=9999)
    is_pinned: bool = False
    is_recurring: bool = False
    recurrence_pattern: Optional[str] = None
    milestone_id: Optional[int] = None


class TaskCreate(TaskBase):
    pass


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[TaskStatus] = None
    priority: Optional[TaskPriority] = None
    category: Optional[TaskCategory] = None
    tags: Optional[str] = None
    due_date: Optional[datetime] = None
    estimated_hours: Optional[float] = Field(None, ge=0, le=9999)
    actual_hours: Optional[float] = Field(None, ge=0, le=9999)
    progress_percentage: Optional[int] = Field(None, ge=0, le=100)
    is_pinned: Optional[bool] = None
    is_recurring: Optional[bool] = None
    recurrence_pattern: Optional[str] = None
    milestone_id: Optional[int] = None


class TaskResponse(BaseModel):
    id: int
    user_id: int
    milestone_id: Optional[int]
    title: str
    description: Optional[str]
    status: TaskStatus
    priority: TaskPriority
    category: TaskCategory
    tags: Optional[str]
    due_date: Optional[datetime]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_hours: Optional[float]
    actual_hours: Optional[float]
    progress_percentage: int
    is_pinned: bool
    is_recurring: bool
    recurrence_pattern: Optional[str]
    subtasks: List[SubtaskResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    id: int
    user_id: int
    milestone_id: Optional[int]
    title: str
    status: TaskStatus
    priority: TaskPriority
    category: TaskCategory
    tags: Optional[str]
    due_date: Optional[datetime]
    progress_percentage: int
    is_pinned: bool
    subtask_count: int = 0
    completed_subtask_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskBulkDelete(BaseModel):
    task_ids: List[int] = Field(..., min_length=1)
