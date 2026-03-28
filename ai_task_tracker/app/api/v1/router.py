"""Central v1 API router – registers all endpoint modules."""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    ai_suggestions,
    auth,
    dashboard,
    milestones,
    notifications,
    subtasks,
    tasks,
    users,
)

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tasks.router)
api_router.include_router(subtasks.router)
api_router.include_router(milestones.router)
api_router.include_router(notifications.router)
api_router.include_router(ai_suggestions.router)
api_router.include_router(dashboard.router)
api_router.include_router(admin.router)
