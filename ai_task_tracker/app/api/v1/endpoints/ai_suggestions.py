"""AI Suggestion endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user_id, get_db
from app.models.ai_suggestion import SuggestionStatus
from app.schemas.ai_suggestion import AISuggestionResponse, SuggestionFeedback
from app.schemas.common import PaginatedResponse, PaginationMeta, SuccessResponse
from app.services.ai_engine import AISuggestionService

router = APIRouter(prefix="/ai-suggestions", tags=["AI Suggestions"])


@router.get("", response_model=PaginatedResponse[AISuggestionResponse])
async def list_suggestions(
    unread_only: bool = Query(False),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """List pending AI suggestions for the current user."""
    skip = (page - 1) * per_page
    suggestions, total = await AISuggestionService.list_for_user(
        db, user_id=user_id, unread_only=unread_only, skip=skip, limit=per_page
    )
    total_pages = max(1, -(-total // per_page))
    return {
        "success": True,
        "data": suggestions,
        "meta": PaginationMeta(
            total=total, page=page, per_page=per_page,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
        ),
    }


@router.post("/generate", response_model=list[AISuggestionResponse])
async def generate_suggestions(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Trigger the AI engine to analyse the current user and generate new suggestions."""
    suggestions = await AISuggestionService.generate_for_user(db, user_id)
    return suggestions


@router.patch("/{suggestion_id}/feedback", response_model=AISuggestionResponse)
async def give_feedback(
    suggestion_id: int,
    data: SuggestionFeedback,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Accept or dismiss a suggestion."""
    from app.core.exceptions import NotFoundError
    suggestion = await AISuggestionService.update_status(db, suggestion_id, user_id, data.status)
    if not suggestion:
        raise NotFoundError("Suggestion")
    return suggestion


@router.patch("/{suggestion_id}/read", response_model=SuccessResponse)
async def mark_suggestion_read(
    suggestion_id: int,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Mark a suggestion as read."""
    await AISuggestionService.mark_read(db, suggestion_id, user_id)
    return SuccessResponse(message="Suggestion marked as read")
