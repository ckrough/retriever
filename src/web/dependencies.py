"""Web dependencies for authentication and authorization."""

from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.responses import RedirectResponse
from starlette.exceptions import HTTPException

from src.config import Settings, get_settings
from src.web.auth_routes import get_current_user_from_cookie


class AuthenticationRequired(HTTPException):
    """Exception raised when authentication is required.

    This triggers a redirect to the login page.
    """

    def __init__(self) -> None:
        super().__init__(status_code=303, detail="Authentication required")


def get_current_user(request: Request) -> dict[str, Any] | None:
    """Get the current user from the request cookie.

    Returns:
        User dict if authenticated, None otherwise.
    """
    return get_current_user_from_cookie(request)


def require_auth(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any] | None:
    """Dependency that requires authentication when enabled.

    When auth is disabled (auth_enabled=False or no JWT secret),
    returns None to allow anonymous access.

    Args:
        request: The incoming request.
        settings: Application settings.

    Returns:
        User dict with user_id, email, and is_admin if authenticated.
        None if auth is disabled.

    Raises:
        AuthenticationRequired: If auth enabled and user is not authenticated.
    """
    # Skip auth if disabled
    if not settings.auth_enabled or not settings.jwt_secret_key:
        return None

    user = get_current_user_from_cookie(request)
    if user is None:
        raise AuthenticationRequired()
    return user


def require_admin(
    user: Annotated[dict[str, Any] | None, Depends(require_auth)],
) -> dict[str, Any] | None:
    """Dependency that requires admin authentication when enabled.

    When auth is disabled, returns None to allow anonymous access.

    Args:
        user: The authenticated user from require_auth, or None if auth disabled.

    Returns:
        User dict if admin, None if auth disabled.

    Raises:
        HTTPException: If auth enabled and user is not an admin.
    """
    # If auth is disabled (user is None from require_auth), allow access
    if user is None:
        return None

    if not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# Exception handler for AuthenticationRequired
async def auth_exception_handler(
    request: Request, _exc: AuthenticationRequired
) -> RedirectResponse:
    """Handle AuthenticationRequired by redirecting to login.

    The next parameter preserves the original URL for post-login redirect.
    """
    login_url = f"/login?next={request.url.path}"
    return RedirectResponse(url=login_url, status_code=303)
