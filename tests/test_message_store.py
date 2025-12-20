"""Tests for conversation message storage."""

import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from src.infrastructure.database import Database
from src.modules.auth.repository import UserRepository
from src.modules.rag.message_store import MessageStore
from src.modules.rag.schemas import Message


@pytest.fixture
async def database() -> Database:
    """Create a temporary test database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        await db.connect()
        yield db
        await db.disconnect()


@pytest.fixture
async def message_store(database: Database) -> MessageStore:
    """Create a message store with test database."""
    return MessageStore(database)


@pytest.fixture
async def test_user_id(database: Database) -> str:
    """Create a test user and return their ID."""
    repo = UserRepository(database)
    user = await repo.create(
        email="test@example.com",
        hashed_password="hashed",
    )
    return str(user.id)


class TestMessageModel:
    """Tests for Message schema."""

    def test_message_creation(self) -> None:
        """Should create a message with all fields."""
        message = Message(
            id=uuid4(),
            user_id=uuid4(),
            role="user",
            content="Hello, world!",
            created_at=datetime.now(UTC),
        )
        assert message.role == "user"
        assert message.content == "Hello, world!"

    def test_message_from_row(self) -> None:
        """Should create message from database row."""
        now = datetime.now(UTC).isoformat()
        row = {
            "id": str(uuid4()),
            "user_id": str(uuid4()),
            "role": "assistant",
            "content": "How can I help?",
            "created_at": now,
        }
        message = Message.from_row(row)
        assert message.role == "assistant"
        assert message.content == "How can I help?"


class TestMessageStore:
    """Tests for MessageStore."""

    @pytest.mark.asyncio
    async def test_save_user_message(
        self, message_store: MessageStore, test_user_id: str
    ) -> None:
        """Should save a user message."""
        from uuid import UUID

        user_id = UUID(test_user_id)
        message = await message_store.save_message(
            user_id=user_id,
            role="user",
            content="What are the shelter hours?",
        )

        assert message.user_id == user_id
        assert message.role == "user"
        assert message.content == "What are the shelter hours?"
        assert message.created_at is not None

    @pytest.mark.asyncio
    async def test_save_assistant_message(
        self, message_store: MessageStore, test_user_id: str
    ) -> None:
        """Should save an assistant message."""
        from uuid import UUID

        user_id = UUID(test_user_id)
        message = await message_store.save_message(
            user_id=user_id,
            role="assistant",
            content="The shelter is open from 9am to 5pm.",
        )

        assert message.role == "assistant"
        assert message.content == "The shelter is open from 9am to 5pm."

    @pytest.mark.asyncio
    async def test_save_message_invalid_role_fails(
        self, message_store: MessageStore, test_user_id: str
    ) -> None:
        """Should reject invalid role."""
        from uuid import UUID

        user_id = UUID(test_user_id)
        with pytest.raises(ValueError, match="Invalid role"):
            await message_store.save_message(
                user_id=user_id,
                role="system",  # Invalid
                content="Invalid message",
            )

    @pytest.mark.asyncio
    async def test_get_recent_messages_empty(
        self, message_store: MessageStore, test_user_id: str
    ) -> None:
        """Should return empty list for user with no messages."""
        from uuid import UUID

        user_id = UUID(test_user_id)
        messages = await message_store.get_recent_messages(user_id)
        assert messages == []

    @pytest.mark.asyncio
    async def test_get_recent_messages_chronological_order(
        self, message_store: MessageStore, test_user_id: str
    ) -> None:
        """Should return messages in chronological order (oldest first)."""
        from uuid import UUID

        user_id = UUID(test_user_id)

        # Save messages in order
        await message_store.save_message(user_id, "user", "First question")
        await message_store.save_message(user_id, "assistant", "First answer")
        await message_store.save_message(user_id, "user", "Second question")
        await message_store.save_message(user_id, "assistant", "Second answer")

        messages = await message_store.get_recent_messages(user_id)

        assert len(messages) == 4
        assert messages[0].content == "First question"
        assert messages[1].content == "First answer"
        assert messages[2].content == "Second question"
        assert messages[3].content == "Second answer"

    @pytest.mark.asyncio
    async def test_get_recent_messages_respects_limit(
        self, message_store: MessageStore, test_user_id: str
    ) -> None:
        """Should respect the limit parameter."""
        from uuid import UUID

        user_id = UUID(test_user_id)

        # Save 5 messages
        for i in range(5):
            await message_store.save_message(user_id, "user", f"Message {i}")

        # Request only 3
        messages = await message_store.get_recent_messages(user_id, limit=3)

        assert len(messages) == 3
        # Should be the 3 most recent, in chronological order
        assert messages[0].content == "Message 2"
        assert messages[1].content == "Message 3"
        assert messages[2].content == "Message 4"

    @pytest.mark.asyncio
    async def test_get_recent_messages_different_users(
        self, database: Database, message_store: MessageStore, test_user_id: str
    ) -> None:
        """Should only return messages for the specified user."""
        from uuid import UUID

        # Create second user
        repo = UserRepository(database)
        user2 = await repo.create(
            email="user2@example.com",
            hashed_password="hashed",
        )

        user1_id = UUID(test_user_id)
        user2_id = user2.id

        # Save messages for both users
        await message_store.save_message(user1_id, "user", "User 1 message")
        await message_store.save_message(user2_id, "user", "User 2 message")

        # Get messages for user 1 only
        messages = await message_store.get_recent_messages(user1_id)

        assert len(messages) == 1
        assert messages[0].content == "User 1 message"

    @pytest.mark.asyncio
    async def test_clear_messages(
        self, message_store: MessageStore, test_user_id: str
    ) -> None:
        """Should delete all messages for a user."""
        from uuid import UUID

        user_id = UUID(test_user_id)

        # Save some messages
        await message_store.save_message(user_id, "user", "Question 1")
        await message_store.save_message(user_id, "assistant", "Answer 1")
        await message_store.save_message(user_id, "user", "Question 2")

        # Clear messages
        deleted = await message_store.clear_messages(user_id)

        assert deleted == 3

        # Verify empty
        messages = await message_store.get_recent_messages(user_id)
        assert messages == []

    @pytest.mark.asyncio
    async def test_clear_messages_empty(
        self, message_store: MessageStore, test_user_id: str
    ) -> None:
        """Should return 0 when clearing for user with no messages."""
        from uuid import UUID

        user_id = UUID(test_user_id)
        deleted = await message_store.clear_messages(user_id)
        assert deleted == 0

    @pytest.mark.asyncio
    async def test_clear_messages_only_affects_specified_user(
        self, database: Database, message_store: MessageStore, test_user_id: str
    ) -> None:
        """Should only clear messages for the specified user."""
        from uuid import UUID

        # Create second user
        repo = UserRepository(database)
        user2 = await repo.create(
            email="user2@example.com",
            hashed_password="hashed",
        )

        user1_id = UUID(test_user_id)
        user2_id = user2.id

        # Save messages for both users
        await message_store.save_message(user1_id, "user", "User 1 message")
        await message_store.save_message(user2_id, "user", "User 2 message")

        # Clear only user 1
        await message_store.clear_messages(user1_id)

        # User 2 should still have messages
        messages = await message_store.get_recent_messages(user2_id)
        assert len(messages) == 1
        assert messages[0].content == "User 2 message"
