"""Authentication API routes."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status

from src.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserResponse,
)
from src.modules.auth.service import AuthenticationError, AuthService

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["authentication"])


# Dependency placeholder - will be replaced with proper DI
_auth_service: AuthService | None = None


def get_auth_service() -> AuthService:
    """Get the auth service instance.

    This is a placeholder that should be configured during app startup.
    """
    if _auth_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service not configured",
        )
    return _auth_service


def set_auth_service(service: AuthService) -> None:
    """Set the auth service instance.

    Called during app startup to configure the service.
    """
    global _auth_service
    _auth_service = service


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account. Only admins can create new users.",
)
async def register(
    data: UserCreate,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> UserResponse:
    """Register a new user.

    For MVP, registration is open. In production, this should be
    protected to admin-only access.
    """
    try:
        user = await auth_service.register(data)
        return UserResponse(
            id=user.id,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Login with email and password",
    description="Authenticate and receive a JWT token.",
)
async def login(
    data: LoginRequest,
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> LoginResponse:
    """Authenticate user and return JWT token."""
    try:
        return await auth_service.login(data.email, data.password)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
