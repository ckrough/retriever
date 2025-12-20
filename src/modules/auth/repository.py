"""User repository for database operations."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import structlog

from src.infrastructure.database import Database
from src.modules.auth.models import User

logger = structlog.get_logger()


class UserRepository:
    """Repository for User CRUD operations.

    Handles all database interactions for the User model.
    """

    def __init__(self, database: Database) -> None:
        """Initialize the repository.

        Args:
            database: Database connection.
        """
        self._db = database

    async def create(
        self,
        email: str,
        hashed_password: str,
        *,
        is_admin: bool = False,
        external_id: str | None = None,
    ) -> User:
        """Create a new user.

        Args:
            email: User's email address.
            hashed_password: Bcrypt-hashed password.
            is_admin: Whether user has admin privileges.
            external_id: Optional external system ID.

        Returns:
            The created User.

        Raises:
            ValueError: If email already exists.
        """
        user_id = uuid4()
        now = datetime.now(timezone.utc).isoformat()

        try:
            await self._db.execute(
                """
                INSERT INTO users (id, email, hashed_password, external_id,
                                   is_active, is_admin, created_at, updated_at)
                VALUES (?, ?, ?, ?, 1, ?, ?, ?)
                """,
                (
                    str(user_id),
                    email,
                    hashed_password,
                    external_id,
                    int(is_admin),
                    now,
                    now,
                ),
            )
        except Exception as e:
            if "UNIQUE constraint failed" in str(e):
                raise ValueError(f"User with email {email} already exists") from e
            raise

        logger.info("user_created", user_id=str(user_id), email=email)

        return User(
            id=user_id,
            email=email,
            hashed_password=hashed_password,
            external_id=external_id,
            is_active=True,
            is_admin=is_admin,
            created_at=datetime.fromisoformat(now),
            updated_at=datetime.fromisoformat(now),
        )

    async def get_by_id(self, user_id: UUID) -> User | None:
        """Get a user by ID.

        Args:
            user_id: The user's UUID.

        Returns:
            User if found, None otherwise.
        """
        row = await self._db.fetch_one(
            "SELECT * FROM users WHERE id = ?",
            (str(user_id),),
        )

        if row is None:
            return None

        return User.from_row(dict(row))

    async def get_by_email(self, email: str) -> User | None:
        """Get a user by email.

        Args:
            email: The user's email address.

        Returns:
            User if found, None otherwise.
        """
        row = await self._db.fetch_one(
            "SELECT * FROM users WHERE email = ?",
            (email.lower(),),
        )

        if row is None:
            return None

        return User.from_row(dict(row))

    async def update(self, user: User) -> User:
        """Update a user.

        Args:
            user: User with updated fields.

        Returns:
            The updated User.
        """
        now = datetime.now(timezone.utc).isoformat()

        await self._db.execute(
            """
            UPDATE users
            SET email = ?, hashed_password = ?, external_id = ?,
                is_active = ?, is_admin = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                user.email,
                user.hashed_password,
                user.external_id,
                int(user.is_active),
                int(user.is_admin),
                now,
                str(user.id),
            ),
        )

        logger.info("user_updated", user_id=str(user.id))

        return User(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            external_id=user.external_id,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            updated_at=datetime.fromisoformat(now),
        )

    async def delete(self, user_id: UUID) -> bool:
        """Delete a user.

        Args:
            user_id: The user's UUID.

        Returns:
            True if deleted, False if not found.
        """
        cursor = await self._db.execute(
            "DELETE FROM users WHERE id = ?",
            (str(user_id),),
        )

        deleted = cursor.rowcount > 0

        if deleted:
            logger.info("user_deleted", user_id=str(user_id))

        return deleted

    async def list_all(self, *, include_inactive: bool = False) -> list[User]:
        """List all users.

        Args:
            include_inactive: Whether to include inactive users.

        Returns:
            List of users.
        """
        if include_inactive:
            rows = await self._db.fetch_all("SELECT * FROM users ORDER BY created_at")
        else:
            rows = await self._db.fetch_all(
                "SELECT * FROM users WHERE is_active = 1 ORDER BY created_at"
            )

        return [User.from_row(dict(row)) for row in rows]

    async def count(self) -> int:
        """Count total users.

        Returns:
            Number of users.
        """
        row = await self._db.fetch_one("SELECT COUNT(*) as count FROM users")
        return int(row["count"]) if row else 0
