from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, tasks, push, ai

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(tasks.router)
api_router.include_router(push.router)
api_router.include_router(ai.router)
