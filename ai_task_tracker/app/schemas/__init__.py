"""Pydantic schemas package."""
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserPublic,
    UserLoginRequest, TokenResponse, RefreshTokenRequest,
    PasswordChangeRequest, AdminUserUpdate,
)
from app.schemas.task import TaskCreate, TaskUpdate, TaskResponse, TaskListResponse
from app.schemas.subtask import SubtaskCreate, SubtaskUpdate, SubtaskResponse
from app.schemas.milestone import MilestoneCreate, MilestoneUpdate, MilestoneResponse
from app.schemas.notification import NotificationResponse, NotificationUpdate
from app.schemas.ai_suggestion import AISuggestionResponse, SuggestionFeedback
from app.schemas.productivity import ProductivityLogResponse, ProductivitySummary
from app.schemas.common import PaginatedResponse, SuccessResponse, ErrorResponse

__all__ = [
    "UserCreate", "UserUpdate", "UserResponse", "UserPublic",
    "UserLoginRequest", "TokenResponse", "RefreshTokenRequest",
    "PasswordChangeRequest", "AdminUserUpdate",
    "TaskCreate", "TaskUpdate", "TaskResponse", "TaskListResponse",
    "SubtaskCreate", "SubtaskUpdate", "SubtaskResponse",
    "MilestoneCreate", "MilestoneUpdate", "MilestoneResponse",
    "NotificationResponse", "NotificationUpdate",
    "AISuggestionResponse", "SuggestionFeedback",
    "ProductivityLogResponse", "ProductivitySummary",
    "PaginatedResponse", "SuccessResponse", "ErrorResponse",
]
