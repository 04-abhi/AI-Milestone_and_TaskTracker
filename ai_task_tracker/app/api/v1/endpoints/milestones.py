"""Milestone endpoints."""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id, get_db
from app.schemas.common import PaginatedResponse, PaginationMeta, SuccessResponse
from app.schemas.milestone import MilestoneCreate, MilestoneResponse, MilestoneUpdate
from app.services.milestone_service import MilestoneService

router = APIRouter(prefix="/milestones", tags=["Milestones"])


@router.post("", response_model=MilestoneResponse, status_code=status.HTTP_201_CREATED)
async def create_milestone(
    data: MilestoneCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Create a new milestone."""
    return await MilestoneService.create(db, user_id, data)


@router.get("", response_model=PaginatedResponse[MilestoneResponse])
async def list_milestones(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List all milestones with optional status filter."""
    skip = (page - 1) * per_page
    milestones, total = await MilestoneService.list_milestones(
        db, user_id=user_id, status=status, skip=skip, limit=per_page
    )
    total_pages = max(1, -(-total // per_page))
    return {
        "success": True,
        "data": milestones,
        "meta": PaginationMeta(
            total=total, page=page, per_page=per_page,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    }


@router.get("/{milestone_id}", response_model=MilestoneResponse)
async def get_milestone(
    milestone_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get a single milestone."""
    return await MilestoneService.get_or_raise(db, milestone_id, user_id)


@router.patch("/{milestone_id}", response_model=MilestoneResponse)
async def update_milestone(
    milestone_id: int,
    data: MilestoneUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Update a milestone."""
    milestone = await MilestoneService.get_or_raise(db, milestone_id, user_id)
    return await MilestoneService.update(db, milestone, data)


@router.delete("/{milestone_id}", response_model=SuccessResponse)
async def delete_milestone(
    milestone_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete a milestone."""
    milestone = await MilestoneService.get_or_raise(db, milestone_id, user_id)
    await MilestoneService.delete(db, milestone)
    return SuccessResponse(message="Milestone deleted")


@router.post("/{milestone_id}/recalculate", response_model=MilestoneResponse)
async def recalculate_milestone_progress(
    milestone_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger progress recalculation for a milestone."""
    milestone = await MilestoneService.get_or_raise(db, milestone_id, user_id)
    await MilestoneService.recalculate_progress(db, milestone_id)
    return await MilestoneService.get_or_raise(db, milestone_id, user_id)
