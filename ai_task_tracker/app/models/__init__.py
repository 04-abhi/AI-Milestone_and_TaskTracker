"""Import all models to ensure they're registered with SQLAlchemy."""
from app.models.user import User, UserSession
from app.models.task import Task
from app.models.subtask import Subtask
from app.models.milestone import Milestone
from app.models.notification import Notification
from app.models.ai_suggestion import AISuggestion
from app.models.productivity import ProductivityLog

__all__ = [
    "User",
    "UserSession",
    "Task",
    "Subtask",
    "Milestone",
    "Notification",
    "AISuggestion",
    "ProductivityLog",
]
