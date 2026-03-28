"""AI Suggestion Pydantic schemas."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.models.ai_suggestion import SuggestionStatus, SuggestionType


class AISuggestionResponse(BaseModel):
    id: int
    user_id: int
    suggestion_type: SuggestionType
    title: str
    message: str
    action_label: Optional[str]
    action_data: Optional[str]
    status: SuggestionStatus
    confidence_score: float
    priority_score: int
    is_read: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class SuggestionFeedback(BaseModel):
    status: SuggestionStatus  # accepted | dismissed
