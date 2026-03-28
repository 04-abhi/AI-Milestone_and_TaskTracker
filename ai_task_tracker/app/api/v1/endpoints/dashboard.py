"""Dashboard endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id, get_db
from app.schemas.productivity import DashboardStats, ProductivitySummary
from app.services.productivity_service import ProductivityService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get aggregated stats for the user dashboard."""
    return await ProductivityService.get_dashboard_stats(db, user_id)


@router.get("/productivity", response_model=ProductivitySummary)
async def get_productivity_summary(
    days: int = Query(30, ge=7, le=365),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get productivity summary over a configurable number of days."""
    return await ProductivityService.get_summary(db, user_id, days)


@router.post("/record-daily-log")
async def record_daily_log(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger daily productivity log recording for today."""
    log = await ProductivityService.record_daily_log(db, user_id)
    return {
        "success": True,
        "message": "Daily log recorded",
        "data": {
            "log_date": str(log.log_date),
            "productivity_score": log.productivity_score,
            "tasks_completed": log.tasks_completed,
            "completion_rate": log.completion_rate,
        },
    }
