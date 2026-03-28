"""Subtask Pydantic schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.subtask import SubtaskStatus


class SubtaskBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    due_date: Optional[datetime] = None
    estimated_minutes: Optional[int] = Field(None, ge=0, le=99999)
    order_index: int = 0


class SubtaskCreate(SubtaskBase):
    pass


class SubtaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    status: Optional[SubtaskStatus] = None
    due_date: Optional[datetime] = None
    estimated_minutes: Optional[int] = Field(None, ge=0, le=99999)
    order_index: Optional[int] = None


class SubtaskResponse(BaseModel):
    id: int
    task_id: int
    title: str
    description: Optional[str]
    status: SubtaskStatus
    order_index: int
    due_date: Optional[datetime]
    completed_at: Optional[datetime]
    estimated_minutes: Optional[int]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SubtaskReorder(BaseModel):
    subtask_ids: list[int] = Field(..., min_length=1)
