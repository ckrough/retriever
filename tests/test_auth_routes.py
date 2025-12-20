"""Tests for web authentication routes."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from src.infrastructure.database import Database
from src.modules.auth.repository import UserRepository
from src.modules.auth.schemas import UserCreate
from src.modules.auth.service import AuthService
from src.web.auth_routes import (
    AUTH_COOKIE_NAME,
    get_current_user_from_cookie,
    router,
    set_auth_service,
)


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
async def auth_service(database: Database) -> AuthService:
    """Create an auth service with test repository."""
    repository = UserRepository(database)
    return AuthService(
        repository,
        jwt_secret="test-secret-key-for-testing-only",
        jwt_expire_hours=24,
    )


@pytest.fixture
def test_app(auth_service: AuthService) -> TestClient:
    """Create a test client with the auth router."""
    from fastapi import FastAPI
    from src.web.templates import templates

    app = FastAPI()
    app.include_router(router)

    # Configure auth service
    set_auth_service(auth_service)

    return TestClient(app)


class TestLoginPage:
    """Tests for GET /login."""

    def test_login_page_renders(self, test_app: TestClient) -> None:
        """Should render login page for unauthenticated users."""
        response = test_app.get("/login")

        assert response.status_code == 200
        assert "Sign in to your account" in response.text
        assert "email" in response.text
        assert "password" in response.text

    def test_login_page_redirects_if_authenticated(
        self, test_app: TestClient, auth_service: AuthService
    ) -> None:
        """Should redirect to home if already logged in."""
        # Create a user and get a valid token
        import asyncio

        async def setup_user() -> str:
            data = UserCreate(email="test@example.com", password="password123")
            user = await auth_service.register(data)
            login_response = auth_service.create_token(user)
            return login_response.access_token

        token = asyncio.get_event_loop().run_until_complete(setup_user())

        # Set the auth cookie
        test_app.cookies.set(AUTH_COOKIE_NAME, token)

        response = test_app.get("/login", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/"


class TestLoginSubmit:
    """Tests for POST /login."""

    @pytest.mark.asyncio
    async def test_login_success_sets_cookie(
        self, test_app: TestClient, auth_service: AuthService
    ) -> None:
        """Should set auth cookie on successful login."""
        # Create a user first
        data = UserCreate(email="test@example.com", password="password123")
        await auth_service.register(data)

        response = test_app.post(
            "/login",
            data={"email": "test@example.com", "password": "password123"},
            follow_redirects=False,
        )

        assert response.status_code == 303
        assert response.headers["location"] == "/"
        assert AUTH_COOKIE_NAME in response.cookies

    @pytest.mark.asyncio
    async def test_login_failure_shows_error(
        self, test_app: TestClient, auth_service: AuthService
    ) -> None:
        """Should show error message on failed login."""
        # Create a user first
        data = UserCreate(email="test@example.com", password="password123")
        await auth_service.register(data)

        response = test_app.post(
            "/login",
            data={"email": "test@example.com", "password": "wrong_password"},
        )

        assert response.status_code == 200
        assert "Invalid email or password" in response.text

    def test_login_nonexistent_user_shows_error(self, test_app: TestClient) -> None:
        """Should show error for non-existent user."""
        response = test_app.post(
            "/login",
            data={"email": "nobody@example.com", "password": "password"},
        )

        assert response.status_code == 200
        assert "Invalid email or password" in response.text


class TestLogout:
    """Tests for GET /logout."""

    @pytest.mark.asyncio
    async def test_logout_clears_cookie(
        self, test_app: TestClient, auth_service: AuthService
    ) -> None:
        """Should clear auth cookie on logout."""
        # Create a user and get a valid token
        data = UserCreate(email="test@example.com", password="password123")
        user = await auth_service.register(data)
        login_response = auth_service.create_token(user)

        # Set the auth cookie
        test_app.cookies.set(AUTH_COOKIE_NAME, login_response.access_token)

        response = test_app.get("/logout", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/login"
        # Cookie should be deleted (empty value or Max-Age=0)
        assert AUTH_COOKIE_NAME in response.headers.get("set-cookie", "").lower()

    def test_logout_without_session_redirects(self, test_app: TestClient) -> None:
        """Should redirect to login even without session."""
        response = test_app.get("/logout", follow_redirects=False)

        assert response.status_code == 303
        assert response.headers["location"] == "/login"


class TestGetCurrentUserFromCookie:
    """Tests for get_current_user_from_cookie helper."""

    @pytest.mark.asyncio
    async def test_valid_cookie_returns_user_dict(
        self, auth_service: AuthService
    ) -> None:
        """Should return user dict for valid cookie."""
        set_auth_service(auth_service)

        # Create user and token
        data = UserCreate(email="test@example.com", password="password123")
        user = await auth_service.register(data)
        login_response = auth_service.create_token(user)

        # Create mock request with cookie
        mock_request = MagicMock()
        mock_request.cookies.get.return_value = login_response.access_token

        user_dict = get_current_user_from_cookie(mock_request)

        assert user_dict is not None
        assert user_dict["email"] == "test@example.com"
        assert user_dict["user_id"] == str(user.id)

    def test_no_cookie_returns_none(self, auth_service: AuthService) -> None:
        """Should return None when no cookie present."""
        set_auth_service(auth_service)

        mock_request = MagicMock()
        mock_request.cookies.get.return_value = None

        user_dict = get_current_user_from_cookie(mock_request)

        assert user_dict is None

    def test_invalid_cookie_returns_none(self, auth_service: AuthService) -> None:
        """Should return None for invalid token."""
        set_auth_service(auth_service)

        mock_request = MagicMock()
        mock_request.cookies.get.return_value = "invalid.token.here"

        user_dict = get_current_user_from_cookie(mock_request)

        assert user_dict is None

    def test_no_auth_service_returns_none(self) -> None:
        """Should return None when auth service not configured."""
        set_auth_service(None)  # type: ignore[arg-type]

        mock_request = MagicMock()

        user_dict = get_current_user_from_cookie(mock_request)

        assert user_dict is None
