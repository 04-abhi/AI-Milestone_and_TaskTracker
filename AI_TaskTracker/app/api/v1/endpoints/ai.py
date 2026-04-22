"""
AI Endpoints
POST /api/v1/ai/plan       — Milestone planner
POST /api/v1/ai/breakdown  — Procrastination recovery breakdown
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.deps import get_current_user
from app.models.user import User
from app.services.ai_service import generate_milestone_plan, generate_breakdown_plan

router = APIRouter(prefix="/ai", tags=["AI"])


# ── Request / Response schemas ──────────────────────────────────────────────

class PlanRequest(BaseModel):
    title: str       = Field(..., min_length=1, max_length=255)
    description: str = Field("", max_length=2000)
    days: int        = Field(..., ge=1, le=365)


class BreakdownRequest(BaseModel):
    title: str            = Field(..., min_length=1, max_length=255)
    description: str      = Field("", max_length=2000)
    due_date: str         = Field("")        # ISO string or empty
    recovery_days: int    = Field(..., ge=1, le=365)
    done_subtasks: list[str]    = Field(default_factory=list)
    pending_subtasks: list[str] = Field(default_factory=list)


# ── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/plan")
async def create_plan(
    data: PlanRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate a day-wise milestone plan using Groq AI.
    Returns structured JSON the frontend renders as editable day cards.
    """
    try:
        plan = await generate_milestone_plan(
            title=data.title,
            description=data.description,
            days=data.days,
        )
        return plan
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {e}")


@router.post("/breakdown")
async def create_breakdown(
    data: BreakdownRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Generate a recovery plan for a procrastinated task.
    Skips already-completed subtasks and plans only remaining work.
    """
    # Calculate days overdue
    days_overdue = 0
    original_due_str = "not set"
    if data.due_date:
        try:
            due = datetime.fromisoformat(data.due_date.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            diff = (now - due).days
            days_overdue = max(0, diff)
            original_due_str = due.strftime("%B %d, %Y")
        except ValueError:
            pass

    try:
        plan = await generate_breakdown_plan(
            title=data.title,
            description=data.description,
            original_due_date=original_due_str,
            days_overdue=days_overdue,
            recovery_days=data.recovery_days,
            done_subtasks=data.done_subtasks,
            pending_subtasks=data.pending_subtasks,
        )
        return plan
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI service error: {e}")
