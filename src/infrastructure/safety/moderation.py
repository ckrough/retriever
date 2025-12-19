"""Content moderation using OpenAI Moderation API."""

from typing import Protocol

import httpx
import structlog

from src.infrastructure.safety.schemas import ModerationResult

logger = structlog.get_logger()


class ModerationProvider(Protocol):
    """Protocol for content moderation providers."""

    async def check(self, text: str) -> ModerationResult:
        """Check if text contains unsafe content.

        Args:
            text: The text to check.

        Returns:
            ModerationResult with flagged status and category details.
        """
        ...


class OpenAIModerator:
    """Content moderator using OpenAI's Moderation API.

    The OpenAI Moderation API is free to use and provides fast (<100ms)
    content classification for harmful content categories.
    """

    MODERATION_URL = "https://api.openai.com/v1/moderations"

    def __init__(
        self,
        api_key: str,
        *,
        timeout_seconds: float = 10.0,
    ) -> None:
        """Initialize the moderator.

        Args:
            api_key: OpenAI API key for moderation requests.
            timeout_seconds: Request timeout in seconds.
        """
        self._api_key = api_key
        self._timeout = timeout_seconds
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

    async def check(self, text: str) -> ModerationResult:
        """Check if text contains unsafe content.

        Args:
            text: The text to check.

        Returns:
            ModerationResult with flagged status and category details.

        Note:
            On API errors, returns a safe result to avoid blocking
            legitimate requests. Errors are logged for monitoring.
        """
        try:
            response = await self._client.post(
                self.MODERATION_URL,
                json={"input": text},
            )
            response.raise_for_status()

            data = response.json()
            result = data["results"][0]

            moderation_result = ModerationResult(
                flagged=result["flagged"],
                categories=result["categories"],
                category_scores=result["category_scores"],
            )

            if moderation_result.flagged:
                # Get list of flagged categories
                flagged_cats = [
                    cat for cat, flagged in result["categories"].items() if flagged
                ]
                logger.warning(
                    "moderation_content_flagged",
                    flagged_categories=flagged_cats,
                    text_preview=text[:100],
                )

            return moderation_result

        except httpx.TimeoutException:
            logger.error("moderation_timeout", text_length=len(text))
            # Fail open - don't block on timeout
            return ModerationResult.safe()

        except httpx.HTTPStatusError as e:
            logger.error(
                "moderation_api_error",
                status_code=e.response.status_code,
                text_length=len(text),
            )
            # Fail open - don't block on API errors
            return ModerationResult.safe()

        except Exception as e:
            logger.error(
                "moderation_unexpected_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            # Fail open
            return ModerationResult.safe()

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()


class NoOpModerator:
    """No-op moderator that always returns safe.

    Use this when moderation is disabled or API key is not configured.
    """

    async def check(self, text: str) -> ModerationResult:  # noqa: ARG002
        """Always returns a safe result.

        Args:
            text: The text to check (ignored).

        Returns:
            ModerationResult marked as safe.
        """
        return ModerationResult.safe()

    async def close(self) -> None:
        """No-op close."""
        pass
