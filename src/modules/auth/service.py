"""Authentication service for user management."""

from datetime import UTC, datetime, timedelta

import jwt
import structlog

from src.modules.auth.models import User
from src.modules.auth.password import hash_password, verify_password
from src.modules.auth.repository import UserRepository
from src.modules.auth.schemas import (
    LoginResponse,
    TokenPayload,
    UserCreate,
    UserResponse,
)

logger = structlog.get_logger()


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class AuthService:
    """Service for authentication operations.

    Handles user registration, login, and token management.
    """

    def __init__(
        self,
        repository: UserRepository,
        *,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        jwt_expire_hours: int = 24,
    ) -> None:
        """Initialize the auth service.

        Args:
            repository: User repository for database operations.
            jwt_secret: Secret key for JWT signing.
            jwt_algorithm: Algorithm for JWT signing.
            jwt_expire_hours: Hours until token expiration.
        """
        self._repo = repository
        self._jwt_secret = jwt_secret
        self._jwt_algorithm = jwt_algorithm
        self._jwt_expire_hours = jwt_expire_hours

    async def register(self, data: UserCreate) -> User:
        """Register a new user.

        Args:
            data: User creation data.

        Returns:
            The created User.

        Raises:
            ValueError: If email already exists.
        """
        hashed = hash_password(data.password)

        user = await self._repo.create(
            email=data.email.lower(),
            hashed_password=hashed,
            is_admin=data.is_admin,
        )

        logger.info("user_registered", user_id=str(user.id), email=user.email)
        return user

    async def authenticate(self, email: str, password: str) -> User:
        """Authenticate a user by email and password.

        Args:
            email: User's email address.
            password: Plain text password.

        Returns:
            The authenticated User.

        Raises:
            AuthenticationError: If authentication fails.
        """
        user = await self._repo.get_by_email(email.lower())

        if user is None:
            logger.warning("auth_failed_user_not_found", email=email)
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            logger.warning("auth_failed_user_inactive", email=email)
            raise AuthenticationError("Account is deactivated")

        if not verify_password(password, user.hashed_password):
            logger.warning("auth_failed_invalid_password", email=email)
            raise AuthenticationError("Invalid email or password")

        logger.info("user_authenticated", user_id=str(user.id), email=email)
        return user

    def create_token(self, user: User) -> LoginResponse:
        """Create a JWT token for a user.

        Args:
            user: The user to create a token for.

        Returns:
            LoginResponse with token and user info.
        """
        now = datetime.now(UTC)
        expires = now + timedelta(hours=self._jwt_expire_hours)

        # JWT requires integer timestamps for exp and iat
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "is_admin": user.is_admin,
            "exp": int(expires.timestamp()),
            "iat": int(now.timestamp()),
        }

        token = jwt.encode(
            payload,
            self._jwt_secret,
            algorithm=self._jwt_algorithm,
        )

        return LoginResponse(
            access_token=token,
            token_type="bearer",  # nosec B106 - OAuth2 token type, not a password
            expires_in=self._jwt_expire_hours * 3600,
            user=UserResponse(
                id=user.id,
                email=user.email,
                is_active=user.is_active,
                is_admin=user.is_admin,
                created_at=user.created_at,
            ),
        )

    def verify_token(self, token: str) -> TokenPayload:
        """Verify and decode a JWT token.

        Args:
            token: JWT token string.

        Returns:
            Decoded token payload.

        Raises:
            AuthenticationError: If token is invalid or expired.
        """
        try:
            payload = jwt.decode(
                token,
                self._jwt_secret,
                algorithms=[self._jwt_algorithm],
            )
            # Convert integer timestamps to datetime for TokenPayload
            return TokenPayload(
                sub=payload["sub"],
                email=payload["email"],
                is_admin=payload["is_admin"],
                exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
                iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
            )

        except jwt.ExpiredSignatureError as e:
            logger.warning("token_expired")
            raise AuthenticationError("Token has expired") from e

        except jwt.InvalidTokenError as e:
            logger.warning("token_invalid", error=str(e))
            raise AuthenticationError("Invalid token") from e

    async def get_user_by_id(self, user_id: str) -> User | None:
        """Get a user by ID.

        Args:
            user_id: User's UUID as string.

        Returns:
            User if found and active, None otherwise.
        """
        from uuid import UUID

        try:
            uuid = UUID(user_id)
        except ValueError:
            return None

        user = await self._repo.get_by_id(uuid)

        if user is None or not user.is_active:
            return None

        return user

    async def login(self, email: str, password: str) -> LoginResponse:
        """Authenticate user and create token.

        Args:
            email: User's email address.
            password: Plain text password.

        Returns:
            LoginResponse with token and user info.

        Raises:
            AuthenticationError: If authentication fails.
        """
        user = await self.authenticate(email, password)
        return self.create_token(user)
