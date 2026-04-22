from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def strong_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Password needs at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password needs at least one number")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    theme: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    theme: Optional[str] = None  # "dark" | "light"


class PasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class RefreshIn(BaseModel):
    refresh_token: str
