"""Authentication service – token management and session handling."""
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError
from app.core.security import create_access_token, create_refresh_token, verify_token
from app.core.config import settings
from app.models.user import User, UserSession
from app.services.user_service import UserService


class AuthService:

    @staticmethod
    async def login(
        db: AsyncSession,
        email: str,
        password: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> dict:
        """Authenticate and return tokens."""
        user = await UserService.authenticate(db, email, password)
        if not user:
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account is disabled. Contact support.")

        access_token = create_access_token(user.id)
        refresh_token = create_refresh_token(user.id)

        # Store session
        session = UserSession(
            user_id=user.id,
            refresh_token=refresh_token,
            device_info=device_info,
            ip_address=ip_address,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
            last_used_at=datetime.now(timezone.utc),
        )
        db.add(session)

        # Update last active
        await UserService.update_last_active(db, user.id)
        await db.flush()

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": user,
        }

    @staticmethod
    async def refresh_tokens(db: AsyncSession, refresh_token: str) -> dict:
        """Exchange a valid refresh token for a new token pair."""
        user_id_str = verify_token(refresh_token, "refresh")
        if not user_id_str:
            raise AuthenticationError("Invalid or expired refresh token")

        # Verify session exists and is active
        session = await db.scalar(
            select(UserSession).where(
                UserSession.refresh_token == refresh_token,
                UserSession.is_active == True,  # noqa: E712
                UserSession.expires_at > datetime.now(timezone.utc),
            )
        )
        if not session:
            raise AuthenticationError("Session expired or revoked")

        user = await UserService.get_by_id(db, int(user_id_str))
        if not user or not user.is_active:
            raise AuthenticationError("User not found or disabled")

        # Rotate tokens
        new_access_token = create_access_token(user.id)
        new_refresh_token = create_refresh_token(user.id)

        # Update session
        session.refresh_token = new_refresh_token
        session.last_used_at = datetime.now(timezone.utc)
        session.expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

        await db.flush()

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": user,
        }

    @staticmethod
    async def logout(db: AsyncSession, refresh_token: str) -> None:
        """Revoke a session."""
        session = await db.scalar(
            select(UserSession).where(UserSession.refresh_token == refresh_token)
        )
        if session:
            session.is_active = False
            await db.flush()

    @staticmethod
    async def logout_all(db: AsyncSession, user_id: int) -> None:
        """Revoke all sessions for a user."""
        sessions = (
            await db.scalars(
                select(UserSession).where(
                    UserSession.user_id == user_id, UserSession.is_active == True  # noqa: E712
                )
            )
        ).all()
        for session in sessions:
            session.is_active = False
        await db.flush()
