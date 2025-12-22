"""Tests for web dependencies (authentication and authorization)."""

from unittest.mock import Mock, patch

import pytest
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.exceptions import HTTPException

from src.config import Settings
from src.web.dependencies import (
    AuthenticationRequired,
    auth_exception_handler,
    get_current_user,
    require_admin,
    require_auth,
)


class TestAuthenticationRequired:
    """Tests for AuthenticationRequired exception."""

    def test_exception_has_correct_status_code(self):
        """Test AuthenticationRequired sets 303 status code."""
        exc = AuthenticationRequired()
        assert exc.status_code == 303
        assert exc.detail == "Authentication required"


class TestGetCurrentUser:
    """Tests for get_current_user dependency."""

    @patch("src.web.dependencies.get_current_user_from_cookie")
    def test_get_current_user_returns_user_dict_when_authenticated(self, mock_get_user):
        """Test get_current_user returns user dict from cookie."""
        mock_get_user.return_value = {"user_id": "test-id", "email": "test@example.com"}
        request = Mock(spec=Request)

        result = get_current_user(request)

        assert result is not None
        assert result["user_id"] == "test-id"
        mock_get_user.assert_called_once_with(request)

    @patch("src.web.dependencies.get_current_user_from_cookie")
    def test_get_current_user_returns_none_when_not_authenticated(self, mock_get_user):
        """Test get_current_user returns None when no session cookie."""
        mock_get_user.return_value = None
        request = Mock(spec=Request)

        result = get_current_user(request)

        assert result is None
        mock_get_user.assert_called_once_with(request)


class TestRequireAuth:
    """Tests for require_auth dependency."""

    def test_require_auth_returns_none_when_auth_disabled(self):
        """Test require_auth returns None when auth is disabled."""
        request = Mock(spec=Request)
        settings = Settings(auth_enabled=False, jwt_secret_key="")

        result = require_auth(request, settings)

        assert result is None

    def test_require_auth_returns_none_when_no_jwt_secret(self):
        """Test require_auth returns None when JWT secret is not configured."""
        request = Mock(spec=Request)
        settings = Settings(auth_enabled=True, jwt_secret_key="")

        result = require_auth(request, settings)

        assert result is None

    @patch("src.web.dependencies.get_current_user_from_cookie")
    def test_require_auth_returns_user_when_authenticated(self, mock_get_user):
        """Test require_auth returns user dict when authenticated."""
        mock_get_user.return_value = {
            "user_id": "test-id",
            "email": "test@example.com",
            "is_admin": False,
        }
        request = Mock(spec=Request)
        settings = Settings(auth_enabled=True, jwt_secret_key="secret-key-123")

        result = require_auth(request, settings)

        assert result is not None
        assert result["user_id"] == "test-id"
        mock_get_user.assert_called_once_with(request)

    @patch("src.web.dependencies.get_current_user_from_cookie")
    def test_require_auth_raises_when_not_authenticated(self, mock_get_user):
        """Test require_auth raises AuthenticationRequired when not authenticated."""
        mock_get_user.return_value = None
        request = Mock(spec=Request)
        settings = Settings(auth_enabled=True, jwt_secret_key="secret-key-123")

        with pytest.raises(AuthenticationRequired):
            require_auth(request, settings)


class TestRequireAdmin:
    """Tests for require_admin dependency."""

    def test_require_admin_returns_none_when_auth_disabled(self):
        """Test require_admin returns None when auth is disabled (user is None)."""
        result = require_admin(user=None)

        assert result is None

    def test_require_admin_returns_user_when_user_is_admin(self):
        """Test require_admin returns user dict when user is admin."""
        user = {"user_id": "admin-id", "email": "admin@example.com", "is_admin": True}

        result = require_admin(user=user)

        assert result is not None
        assert result["user_id"] == "admin-id"
        assert result["is_admin"] is True

    def test_require_admin_raises_403_when_user_is_not_admin(self):
        """Test require_admin raises 403 when user is not admin."""
        user = {"user_id": "user-id", "email": "user@example.com", "is_admin": False}

        with pytest.raises(HTTPException) as exc_info:
            require_admin(user=user)

        assert exc_info.value.status_code == 403
        assert exc_info.value.detail == "Admin access required"


class TestAuthExceptionHandler:
    """Tests for auth_exception_handler."""

    @pytest.mark.asyncio
    async def test_auth_exception_handler_redirects_to_login(self):
        """Test auth_exception_handler redirects to login with next parameter."""
        request = Mock(spec=Request)
        request.url.path = "/protected/page"
        exc = AuthenticationRequired()

        response = await auth_exception_handler(request, exc)

        assert isinstance(response, RedirectResponse)
        assert response.status_code == 303
        assert response.headers["location"] == "/login?next=/protected/page"
