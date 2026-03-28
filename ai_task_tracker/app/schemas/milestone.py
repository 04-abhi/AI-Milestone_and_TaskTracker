"""Milestone Pydantic schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from app.models.milestone import MilestoneStatus


class MilestoneBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    color: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")
    icon: Optional[str] = Field(None, max_length=50)
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None


class MilestoneCreate(MilestoneBase):
    pass


class MilestoneUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    color: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")
    icon: Optional[str] = None
    status: Optional[MilestoneStatus] = None
    start_date: Optional[datetime] = None
    due_date: Optional[datetime] = None


class MilestoneResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str]
    color: str
    icon: Optional[str]
    status: MilestoneStatus
    start_date: Optional[datetime]
    due_date: Optional[datetime]
    completed_at: Optional[datetime]
    progress_percentage: int
    total_tasks: int
    completed_tasks: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
