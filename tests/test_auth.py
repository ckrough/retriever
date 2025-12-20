"""Tests for authentication module."""

import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

from src.infrastructure.database import Database
from src.modules.auth import (
    AuthenticationError,
    AuthService,
    hash_password,
    verify_password,
)
from src.modules.auth.models import User
from src.modules.auth.repository import UserRepository


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
async def repository(database: Database) -> UserRepository:
    """Create a user repository with test database."""
    return UserRepository(database)


class TestUserModel:
    """Tests for User model."""

    def test_user_creation(self) -> None:
        """Should create a user with all fields."""
        user = User(
            id=uuid4(),
            email="test@example.com",
            hashed_password="hashed",
            external_id=None,
            is_active=True,
            is_admin=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert user.email == "test@example.com"
        assert user.is_active
        assert not user.is_admin

    def test_user_from_row(self) -> None:
        """Should create user from database row."""
        now = datetime.now(timezone.utc).isoformat()
        row = {
            "id": str(uuid4()),
            "email": "test@example.com",
            "hashed_password": "hashed",
            "external_id": None,
            "is_active": 1,
            "is_admin": 0,
            "created_at": now,
            "updated_at": now,
        }
        user = User.from_row(row)
        assert user.email == "test@example.com"
        assert user.is_active
        assert not user.is_admin


class TestUserRepository:
    """Tests for UserRepository."""

    @pytest.mark.asyncio
    async def test_create_user(self, repository: UserRepository) -> None:
        """Should create a new user."""
        user = await repository.create(
            email="test@example.com",
            hashed_password="hashed_password",
        )

        assert user.email == "test@example.com"
        assert user.is_active
        assert not user.is_admin

    @pytest.mark.asyncio
    async def test_create_admin_user(self, repository: UserRepository) -> None:
        """Should create an admin user."""
        user = await repository.create(
            email="admin@example.com",
            hashed_password="hashed_password",
            is_admin=True,
        )

        assert user.is_admin

    @pytest.mark.asyncio
    async def test_create_duplicate_email_fails(
        self, repository: UserRepository
    ) -> None:
        """Should fail when creating user with duplicate email."""
        await repository.create(
            email="test@example.com",
            hashed_password="hashed_password",
        )

        with pytest.raises(ValueError, match="already exists"):
            await repository.create(
                email="test@example.com",
                hashed_password="another_password",
            )

    @pytest.mark.asyncio
    async def test_get_by_id(self, repository: UserRepository) -> None:
        """Should get user by ID."""
        created = await repository.create(
            email="test@example.com",
            hashed_password="hashed_password",
        )

        found = await repository.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id
        assert found.email == created.email

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repository: UserRepository) -> None:
        """Should return None for non-existent ID."""
        found = await repository.get_by_id(uuid4())
        assert found is None

    @pytest.mark.asyncio
    async def test_get_by_email(self, repository: UserRepository) -> None:
        """Should get user by email."""
        await repository.create(
            email="test@example.com",
            hashed_password="hashed_password",
        )

        found = await repository.get_by_email("test@example.com")

        assert found is not None
        assert found.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_get_by_email_not_found(self, repository: UserRepository) -> None:
        """Should return None for non-existent email."""
        found = await repository.get_by_email("nonexistent@example.com")
        assert found is None

    @pytest.mark.asyncio
    async def test_update_user(self, repository: UserRepository) -> None:
        """Should update user fields."""
        user = await repository.create(
            email="test@example.com",
            hashed_password="hashed_password",
        )

        user.is_admin = True
        updated = await repository.update(user)

        assert updated.is_admin
        assert updated.updated_at > user.created_at

    @pytest.mark.asyncio
    async def test_delete_user(self, repository: UserRepository) -> None:
        """Should delete user."""
        user = await repository.create(
            email="test@example.com",
            hashed_password="hashed_password",
        )

        deleted = await repository.delete(user.id)
        assert deleted

        found = await repository.get_by_id(user.id)
        assert found is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent_user(self, repository: UserRepository) -> None:
        """Should return False when deleting non-existent user."""
        deleted = await repository.delete(uuid4())
        assert not deleted

    @pytest.mark.asyncio
    async def test_list_all(self, repository: UserRepository) -> None:
        """Should list all active users."""
        await repository.create(
            email="user1@example.com",
            hashed_password="hashed",
        )
        await repository.create(
            email="user2@example.com",
            hashed_password="hashed",
        )

        users = await repository.list_all()
        assert len(users) == 2

    @pytest.mark.asyncio
    async def test_count(self, repository: UserRepository) -> None:
        """Should count users."""
        assert await repository.count() == 0

        await repository.create(
            email="test@example.com",
            hashed_password="hashed",
        )

        assert await repository.count() == 1


class TestPasswordHashing:
    """Tests for password hashing utilities."""

    def test_hash_password(self) -> None:
        """Should hash password."""
        password = "secure_password123"
        hashed = hash_password(password)

        assert hashed != password
        assert hashed.startswith("$2")  # bcrypt prefix

    def test_verify_password_correct(self) -> None:
        """Should verify correct password."""
        password = "secure_password123"
        hashed = hash_password(password)

        assert verify_password(password, hashed)

    def test_verify_password_incorrect(self) -> None:
        """Should reject incorrect password."""
        hashed = hash_password("correct_password")

        assert not verify_password("wrong_password", hashed)

    def test_different_hashes_for_same_password(self) -> None:
        """Should generate different hashes due to salt."""
        password = "same_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)


class TestAuthService:
    """Tests for AuthService."""

    @pytest.fixture
    async def auth_service(self, repository: UserRepository) -> AuthService:
        """Create an auth service with test repository."""
        return AuthService(
            repository,
            jwt_secret="test-secret-key-for-testing-only",
            jwt_expire_hours=24,
        )

    @pytest.mark.asyncio
    async def test_register_user(self, auth_service: AuthService) -> None:
        """Should register a new user."""
        from src.modules.auth.schemas import UserCreate

        data = UserCreate(email="test@example.com", password="password123")
        user = await auth_service.register(data)

        assert user.email == "test@example.com"
        assert user.is_active
        assert not user.is_admin

    @pytest.mark.asyncio
    async def test_register_admin(self, auth_service: AuthService) -> None:
        """Should register an admin user."""
        from src.modules.auth.schemas import UserCreate

        data = UserCreate(email="admin@example.com", password="password123", is_admin=True)
        user = await auth_service.register(data)

        assert user.is_admin

    @pytest.mark.asyncio
    async def test_authenticate_success(self, auth_service: AuthService) -> None:
        """Should authenticate with correct credentials."""
        from src.modules.auth.schemas import UserCreate

        data = UserCreate(email="test@example.com", password="password123")
        await auth_service.register(data)

        user = await auth_service.authenticate("test@example.com", "password123")
        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self, auth_service: AuthService) -> None:
        """Should fail with wrong password."""
        from src.modules.auth.schemas import UserCreate

        data = UserCreate(email="test@example.com", password="password123")
        await auth_service.register(data)

        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await auth_service.authenticate("test@example.com", "wrong_password")

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(
        self, auth_service: AuthService
    ) -> None:
        """Should fail for non-existent user."""
        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await auth_service.authenticate("nobody@example.com", "password")

    @pytest.mark.asyncio
    async def test_create_and_verify_token(self, auth_service: AuthService) -> None:
        """Should create and verify JWT token."""
        from src.modules.auth.schemas import UserCreate

        data = UserCreate(email="test@example.com", password="password123")
        user = await auth_service.register(data)

        response = auth_service.create_token(user)
        assert response.access_token
        assert response.token_type == "bearer"
        assert response.user.email == "test@example.com"

        payload = auth_service.verify_token(response.access_token)
        assert payload.sub == str(user.id)
        assert payload.email == "test@example.com"

    def test_verify_invalid_token(self, auth_service: AuthService) -> None:
        """Should reject invalid token."""
        with pytest.raises(AuthenticationError, match="Invalid token"):
            auth_service.verify_token("invalid.token.here")

    @pytest.mark.asyncio
    async def test_login(self, auth_service: AuthService) -> None:
        """Should login and return token."""
        from src.modules.auth.schemas import UserCreate

        data = UserCreate(email="test@example.com", password="password123")
        await auth_service.register(data)

        response = await auth_service.login("test@example.com", "password123")
        assert response.access_token
        assert response.user.email == "test@example.com"
