"""FastAPI dependency injection functions."""
from typing import AsyncGenerator, Optional

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.security import verify_token
from app.db.session import get_db

security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> int:
    """Extract and validate the current user from JWT token."""
    if not credentials:
        raise AuthenticationError("Missing authentication token")

    user_id = verify_token(credentials.credentials, "access")
    if not user_id:
        raise AuthenticationError("Invalid or expired token")

    # Import here to avoid circular imports
    from app.services.user_service import UserService

    user = await UserService.get_by_id(db, int(user_id))
    if not user:
        raise AuthenticationError("User not found")
    if not user.is_active:
        raise AuthenticationError("User account is disabled")

    return user.id


async def get_current_user(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user object."""
    from app.services.user_service import UserService
    return await UserService.get_by_id(db, user_id)


async def get_current_admin_user(
    current_user=Depends(get_current_user),
):
    """Require admin role."""
    if not current_user.is_admin:
        raise AuthorizationError("Admin access required")
    return current_user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """Get current user if authenticated, else None."""
    if not credentials:
        return None
    try:
        user_id = verify_token(credentials.credentials, "access")
        if not user_id:
            return None
        from app.services.user_service import UserService
        return await UserService.get_by_id(db, int(user_id))
    except Exception:
        return None
