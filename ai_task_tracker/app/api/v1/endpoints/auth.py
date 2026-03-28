"""Authentication endpoints."""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.schemas.user import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLoginRequest,
    UserResponse,
)
from app.schemas.common import SuccessResponse
from app.services.auth_service import AuthService
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user account."""
    user = await UserService.create(db, data)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLoginRequest, request: Request, db: AsyncSession = Depends(get_db)):
    """Authenticate and receive access + refresh tokens."""
    ip = request.client.host if request.client else None
    result = await AuthService.login(
        db,
        email=data.email,
        password=data.password,
        device_info=data.device_info,
        ip_address=ip,
    )
    return result


@router.post("/refresh", response_model=TokenResponse)
async def refresh(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Exchange a valid refresh token for a new token pair."""
    result = await AuthService.refresh_tokens(db, data.refresh_token)
    return result


@router.post("/logout", response_model=SuccessResponse)
async def logout(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """Invalidate a refresh token (log out from current device)."""
    await AuthService.logout(db, data.refresh_token)
    return SuccessResponse(message="Logged out successfully")


@router.post("/logout-all", response_model=SuccessResponse)
async def logout_all(
    current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Invalidate all sessions for the current user."""
    await AuthService.logout_all(db, current_user.id)
    return SuccessResponse(message="All sessions revoked")


@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return current_user
