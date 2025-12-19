"""Web routes for server-rendered pages."""

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, Response

from src.api.rate_limit import get_rate_limit_string, limiter
from src.config import Settings, get_settings
from src.infrastructure.llm import LLMProviderError, OpenRouterProvider
from src.infrastructure.llm.openrouter import DEFAULT_SYSTEM_PROMPT
from src.web.templates import templates

logger = structlog.get_logger()

router = APIRouter()

# Input constraints
MAX_QUESTION_LENGTH = 2000


def get_llm_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> OpenRouterProvider | None:
    """Get the LLM provider if configured, None otherwise.

    Returns None when API key is not set, allowing graceful fallback
    to hardcoded responses during development/testing.
    """
    if settings.openrouter_api_key is None:
        return None

    return OpenRouterProvider(
        api_key=settings.openrouter_api_key.get_secret_value(),
        default_model=settings.llm_model,
        timeout_seconds=settings.llm_timeout_seconds,
        circuit_breaker_fail_max=settings.circuit_breaker_fail_max,
        circuit_breaker_timeout=settings.circuit_breaker_timeout,
    )


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    """Render the main chat page."""
    return templates.TemplateResponse(
        request=request,
        name="index.html",
    )


@router.post("/ask", response_class=HTMLResponse)
@limiter.limit(get_rate_limit_string)
async def ask(
    request: Request,
    question: Annotated[str, Form(min_length=1, max_length=MAX_QUESTION_LENGTH)],
    llm_provider: Annotated[OpenRouterProvider | None, Depends(get_llm_provider)],
) -> Response:
    """Handle a question submission and return the answer fragment."""
    # If no LLM provider configured, use fallback response
    if llm_provider is None:
        logger.warning("llm_not_configured", message="Using fallback response")
        answer = (
            "Hello! I'm GoodPuppy, the volunteer assistant. "
            "I'll be able to answer questions about shelter policies and procedures "
            "once I'm fully set up. (LLM not configured)"
        )
        return templates.TemplateResponse(
            request=request,
            name="partials/message_pair.html",
            context={"question": question, "answer": answer},
        )

    # Call the LLM
    try:
        answer = await llm_provider.complete(
            system_prompt=DEFAULT_SYSTEM_PROMPT,
            user_message=question,
        )

        return templates.TemplateResponse(
            request=request,
            name="partials/message_pair.html",
            context={"question": question, "answer": answer},
        )

    except LLMProviderError as e:
        logger.error(
            "llm_error",
            error=str(e),
            provider=e.provider,
            question_length=len(question),
        )

        return templates.TemplateResponse(
            request=request,
            name="partials/error_message.html",
            context={
                "question": question,
                "error_message": "Sorry, I'm having trouble connecting right now. Please try again in a moment.",
            },
        )
