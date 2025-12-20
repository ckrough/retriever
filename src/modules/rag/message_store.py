"""Message store for conversation history."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import structlog

from src.infrastructure.database import Database
from src.modules.rag.schemas import Message

logger = structlog.get_logger()


class MessageStore:
    """Repository for conversation message storage.

    Handles saving and retrieving messages for conversation history.
    Messages are stored per-user and retrieved in chronological order.
    """

    def __init__(self, database: Database) -> None:
        """Initialize the message store.

        Args:
            database: Database connection.
        """
        self._db = database

    async def save_message(
        self,
        user_id: UUID,
        role: str,
        content: str,
    ) -> Message:
        """Save a conversation message.

        Args:
            user_id: The user's UUID.
            role: Message role ('user' or 'assistant').
            content: The message content.

        Returns:
            The created Message.

        Raises:
            ValueError: If role is invalid.
        """
        if role not in ("user", "assistant"):
            raise ValueError(f"Invalid role: {role}. Must be 'user' or 'assistant'.")

        message_id = uuid4()
        created_at = datetime.now(UTC)

        await self._db.execute(
            """
            INSERT INTO messages (id, user_id, role, content, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                str(message_id),
                str(user_id),
                role,
                content,
                created_at.isoformat(),
            ),
        )

        logger.debug(
            "message_saved",
            message_id=str(message_id),
            user_id=str(user_id),
            role=role,
            content_length=len(content),
        )

        return Message(
            id=message_id,
            user_id=user_id,
            role=role,
            content=content,
            created_at=created_at,
        )

    async def get_recent_messages(
        self,
        user_id: UUID,
        limit: int = 20,
    ) -> list[Message]:
        """Get recent messages for a user.

        Retrieves the most recent messages in chronological order
        (oldest first) for use as conversation context.

        Args:
            user_id: The user's UUID.
            limit: Maximum number of messages to retrieve.

        Returns:
            List of messages in chronological order (oldest first).
        """
        # Fetch most recent messages (descending order)
        rows = await self._db.fetch_all(
            """
            SELECT id, user_id, role, content, created_at
            FROM messages
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (str(user_id), limit),
        )

        # Reverse to get chronological order (oldest first)
        messages = [Message.from_row(dict(row)) for row in reversed(rows)]

        logger.debug(
            "messages_retrieved",
            user_id=str(user_id),
            count=len(messages),
            limit=limit,
        )

        return messages

    async def clear_messages(self, user_id: UUID) -> int:
        """Delete all messages for a user.

        Args:
            user_id: The user's UUID.

        Returns:
            Number of messages deleted.
        """
        cursor = await self._db.execute(
            "DELETE FROM messages WHERE user_id = ?",
            (str(user_id),),
        )

        deleted = cursor.rowcount

        if deleted > 0:
            logger.info(
                "messages_cleared",
                user_id=str(user_id),
                count=deleted,
            )

        return deleted
