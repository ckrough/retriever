"""Authentication module for user management and sessions."""

from src.modules.auth.models import User
from src.modules.auth.password import hash_password, verify_password
from src.modules.auth.repository import UserRepository
from src.modules.auth.schemas import (
    LoginRequest,
    LoginResponse,
    TokenPayload,
    UserCreate,
    UserResponse,
)
from src.modules.auth.service import AuthenticationError, AuthService

__all__ = [
    "AuthService",
    "AuthenticationError",
    "LoginRequest",
    "LoginResponse",
    "TokenPayload",
    "User",
    "UserCreate",
    "UserRepository",
    "UserResponse",
    "hash_password",
    "verify_password",
]
