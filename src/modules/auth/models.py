"""User domain model."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass
class User:
    """User domain model.

    Represents a volunteer user who can log in to the Q&A system.

    Attributes:
        id: Unique user identifier.
        email: User's email address (used for login).
        hashed_password: Bcrypt-hashed password.
        external_id: Optional ID for future volunteer system integration.
        is_active: Whether the user account is active.
        is_admin: Whether the user has admin privileges.
        created_at: When the user was created.
        updated_at: When the user was last updated.
    """

    id: UUID
    email: str
    hashed_password: str
    external_id: str | None
    is_active: bool
    is_admin: bool
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: dict[str, object]) -> "User":
        """Create a User from a database row.

        Args:
            row: Database row as a dictionary.

        Returns:
            User instance.
        """
        return cls(
            id=UUID(str(row["id"])),
            email=str(row["email"]),
            hashed_password=str(row["hashed_password"]),
            external_id=str(row["external_id"]) if row["external_id"] else None,
            is_active=bool(row["is_active"]),
            is_admin=bool(row["is_admin"]),
            created_at=datetime.fromisoformat(str(row["created_at"])),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )
