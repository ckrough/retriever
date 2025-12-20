"""Pydantic schemas for authentication API."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for creating a new user."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    is_admin: bool = False


class UserResponse(BaseModel):
    """Schema for user response (excludes sensitive data)."""

    id: UUID
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime


class LoginRequest(BaseModel):
    """Schema for login request."""

    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Schema for login response with JWT token."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # Seconds until expiration
    user: UserResponse


class TokenPayload(BaseModel):
    """Schema for JWT token payload."""

    sub: str  # Subject (user ID)
    email: str
    is_admin: bool
    exp: datetime  # Expiration time
    iat: datetime  # Issued at time
