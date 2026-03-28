"""User profile endpoints."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.exceptions import NotFoundError
from app.schemas.common import SuccessResponse
from app.schemas.user import PasswordChangeRequest, UserResponse, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_profile(current_user=Depends(get_current_user)):
    """Get the current user's full profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_profile(
    data: UserUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current user's profile."""
    updated = await UserService.update(db, current_user, data)
    return updated


@router.post("/me/change-password", response_model=SuccessResponse)
async def change_password(
    data: PasswordChangeRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change the current user's password."""
    from app.core.exceptions import AuthenticationError
    success = await UserService.change_password(
        db, current_user, data.current_password, data.new_password
    )
    if not success:
        raise AuthenticationError("Current password is incorrect")
    return SuccessResponse(message="Password changed successfully")


@router.delete("/me", response_model=SuccessResponse)
async def delete_account(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Soft-delete the current user's account."""
    await UserService.soft_delete(db, current_user)
    return SuccessResponse(message="Account deleted successfully")
