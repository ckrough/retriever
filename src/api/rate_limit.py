"""Rate limiting configuration using slowapi."""

from fastapi import Request, Response
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import HTMLResponse

from src.config import get_settings


def _get_rate_limit_key(request: Request) -> str:
    """Get the rate limit key from the request.

    Uses remote address for now. Will be updated to use user ID
    after authentication is implemented (Increment 7).
    """
    addr: str = get_remote_address(request)
    return addr


# Create limiter instance
limiter = Limiter(key_func=_get_rate_limit_key)


def get_rate_limit_string() -> str:
    """Get the rate limit string from settings."""
    settings = get_settings()
    return f"{settings.rate_limit_requests}/{settings.rate_limit_window}"


async def rate_limit_exceeded_handler(
    request: Request,
    _exc: RateLimitExceeded,
) -> Response:
    """Handle rate limit exceeded errors with a user-friendly message."""
    # For HTMX requests, return an HTML fragment
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            content="""
            <div class="flex gap-3">
                <div class="flex-shrink-0 w-8 h-8 bg-red-100 rounded-full flex items-center justify-center text-sm">
                    ⚠️
                </div>
                <div class="bg-red-50 border border-red-200 rounded-lg shadow-sm p-3 max-w-[80%]">
                    <p class="text-red-700">
                        Too many requests. Please wait a moment before asking another question.
                    </p>
                </div>
            </div>
            """,
            status_code=429,
        )

    # For API requests, return JSON
    return Response(
        content='{"error": "rate_limit_exceeded", "message": "Too many requests. Please wait a moment before asking another question."}',
        status_code=429,
        media_type="application/json",
    )
