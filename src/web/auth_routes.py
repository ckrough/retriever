"""Web authentication routes for login/logout."""

from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse

from src.modules.auth.service import AuthenticationError, AuthService
from src.web.templates import templates

logger = structlog.get_logger()

router = APIRouter()

# Cookie configuration
AUTH_COOKIE_NAME = "auth_token"
AUTH_COOKIE_MAX_AGE = 24 * 60 * 60  # 24 hours in seconds

# Dependency placeholder - configured during app startup
_auth_service: AuthService | None = None


def get_auth_service() -> AuthService | None:
    """Get the auth service instance, or None if not configured."""
    return _auth_service


def set_auth_service(service: AuthService) -> None:
    """Set the auth service instance during app startup."""
    global _auth_service
    _auth_service = service


def get_current_user_from_cookie(request: Request) -> dict[str, Any] | None:
    """Extract and verify user from auth cookie.

    Args:
        request: FastAPI request object.

    Returns:
        Token payload as dict if valid, None otherwise.
    """
    auth_service = get_auth_service()
    if auth_service is None:
        return None

    token = request.cookies.get(AUTH_COOKIE_NAME)
    if not token:
        return None

    try:
        payload = auth_service.verify_token(token)
        return {
            "user_id": payload.sub,
            "email": payload.email,
            "is_admin": payload.is_admin,
        }
    except AuthenticationError:
        return None


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, next: str | None = None) -> Response:
    """Render the login page.

    Args:
        request: The incoming request.
        next: Optional URL to redirect to after login.
    """
    # If already logged in, redirect to home or next URL
    user = get_current_user_from_cookie(request)
    if user:
        redirect_url = next if next else "/"
        return RedirectResponse(url=redirect_url, status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="auth/login.html",
        context={"error": None, "email": None, "next": next},
    )


@router.post("/login", response_class=HTMLResponse)
async def login_submit(
    request: Request,
    email: Annotated[str, Form()],
    password: Annotated[str, Form()],
    next: Annotated[str | None, Form()] = None,
) -> Response:
    """Handle login form submission.

    Args:
        request: The incoming request.
        email: User's email address.
        password: User's password.
        next: Optional URL to redirect to after login.
    """
    auth_service = get_auth_service()

    if auth_service is None:
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"error": "Authentication not configured", "email": email, "next": next},
        )

    try:
        login_response = await auth_service.login(email, password)

        # Redirect to next URL or home
        redirect_url = next if next else "/"
        response = RedirectResponse(url=redirect_url, status_code=303)
        response.set_cookie(
            key=AUTH_COOKIE_NAME,
            value=login_response.access_token,
            max_age=AUTH_COOKIE_MAX_AGE,
            httponly=True,  # Prevent JavaScript access
            samesite="lax",  # CSRF protection
            secure=False,  # Set to True in production with HTTPS
        )

        logger.info("user_logged_in", email=email)
        return response

    except AuthenticationError as e:
        logger.warning("login_failed", email=email, error=str(e))
        return templates.TemplateResponse(
            request=request,
            name="auth/login.html",
            context={"error": str(e), "email": email, "next": next},
        )


@router.get("/logout")
async def logout(request: Request) -> Response:
    """Log out the user by clearing the auth cookie."""
    user = get_current_user_from_cookie(request)
    if user:
        logger.info("user_logged_out", email=user.get("email"))

    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key=AUTH_COOKIE_NAME)
    return response
